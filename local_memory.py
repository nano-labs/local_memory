# -​*- coding: utf-8 -*​-
"""Lib para criar um cache em RAM."""

import os
import mmap
from datetime import datetime
from tempfile import gettempdir
import time
from random import randint
try:
    import simplejson as json
except ImportError:
    import json


def now_seconds():
    """Retorna datetime.now() em segundos."""
    return int(time.mktime(datetime.now().timetuple()))


class SharedMemoryDict(object):

    u"""
    Cria um Dict-like Object residente em memória compartilhada.

    Use com:

    # Processo 1:

    >>> with SharedMemoryDict(name="foo") as foo:
    ...    foo['bar'] = "Hello World"
    ...

    # Processo 2:

    >>> with SharedMemoryDict(name="foo") as foo:
    ...    print foo['bar']
    ...
    Hello World
    """

    def __init__(self, name=None, size=8192, file_location=None,
                 force_flush=False):
        u"""
        Conecta-se a chave 'name' ou cria se não houver.

        name: Nome do arquivo que será usado como endereçamento de memória
        size: Quantos caracteres serão alocados na memoria.
        file_location: Onde será guardado o arquivo de endereçamento
        force_flush: Força limpar o conteudo do file descriptor

        São adicionados 5 caracteres ao fim do arquivo para contar os clients.
        """
        name = name or '%010d' % randint(0, 9999999999)
        file_location = file_location or gettempdir() or "."
        shared_file = os.path.join(file_location, 'mmap_%s' % name)

        if not os.path.exists(shared_file) or force_flush:
            self.__class__.flush_file(shared_file, size)
        f = open(shared_file, 'r+b')

        self.opened_file = f
        mm = mmap.mmap(f.fileno(), 0)
        self.mm = mm
        self.shared_file = shared_file
        self.size = size
        self.name = name
        self.connected_clients += 1
        self.closed = False

    @classmethod
    def flush_file(cls, file_name, size=8192):
        u"""Limpa o conteúdo de um arquivo a ser usado como file descriptor."""
        f = open(file_name, 'wb')
        f.write("{}%s00000" % (" " * (size - 2), ))
        f.close()
        # os.chmod(file_name, 0777)

    def _dump_data(self):
        u"""Retorna todo o conteúdo."""
        self.mm.seek(0)
        return self.mm.read(self.size)

    def __dir__(self):
        """Adiciona 'connected_clients' a lista do comando 'dir'."""
        return ['connected_clients']

    def __getattr__(self, attr):
        """Getter."""
        if attr == 'connected_clients':
            self.mm.seek(self.size)
            return int(self.mm.read(5))
        else:
            return super(SharedMemoryDict, self).__getattr__(attr)

    def __setattr__(self, attr, value):
        """Setter."""
        if attr == 'connected_clients':
            value = '%05d' % value
            self.mm.seek(self.size)
            self.mm.write(value)
        else:
            return super(SharedMemoryDict, self).__setattr__(attr, value)

    def get_dict(self):
        u"""Retorna o conteúdo da memória em um dict."""
        data = json.loads(self._dump_data())
        return data

    def get(self, key, default=None):
        u"""Não seria um dict-like se não tivesse um .get."""
        return self.get_dict().get(key, default)

    def keys(self):
        u"""Retorna todas as chaves do dicionário em RAM."""
        return self.get_dict().keys()

    def pop(self, key):
        """Retorna o valor da chave e a remove."""
        value = self.get("key")
        self.remove(key)
        return value

    def delete(self, key):
        """Remove uma chave."""
        whole_data = self.get_dict()
        whole_data.pop(key)
        self.write(whole_data)

    def remove(self, *args, **kwargs):
        """Mesmo que delete()."""
        return self.delete(*args, **kwargs)

    def write(self, dict_data):
        u"""De fato escreve o conteúdo na memória."""
        self._flush_data()
        json_string = json.dumps(dict_data)
        self.mm.write(json_string)

    def close(self):
        u"""Fecha a conexão, subtrai um client e apaga o fd se possível."""
        if not self.closed:
            self.connected_clients -= 1
            if self.connected_clients <= 0:
                os.remove(self.shared_file)
            self.mm.close()
            self.opened_file.close()
            self.closed = True

    def _flush_memory(self):
        u"""Limpa todo o conteúdo e dados de expiração da memória."""
        self.mm.seek(0)
        self.mm.write("{}%s" % (" " * (self.size - 2), ))
        self.mm.seek(0)

    def __dict__(self):
        """Alias para o get_dict()."""
        return self.get_dict()

    def __getitem__(self, item):
        u"""
        Permite ler um valor da memória usando uma chave.

        Ex:
        >>> obj = SharedMemoryDict(name='foo')
        >>> print obj['bar']
        Hello World
        """
        return self.get(item)

    def __setitem__(self, key, value):
        u"""
        Permite escrever um valor da memória usando uma chave.

        Ex:
        >>> obj = SharedMemoryDict(name='foo')
        >>> obj['bar'] = 'Hello World'
        >>> print obj['bar']
        Hello World
        """
        whole_data = self.get_dict()
        whole_data[key] = value
        self.write(whole_data)

    def __description__(self):
        """Retorna Unicode com resumo do objeto."""
        return u'SharedMemoryDict Object\nName: \t\t"%s"\nFile: \t\t%s\nSize: \t\t%s characters\nClients: \t%s\nData:\n"%s"' % (
            self.name, self.shared_file, self.size, self.connected_clients, self._dump_data())

    def __repr__(self):
        """Preenchendo requisitos de objeto python."""
        return str(self.__dict__())

    def __str__(self):
        """Preenchendo requisitos de objeto python."""
        return self.__unicode__()

    def __enter__(self):
        u"""Se define ao ser instânciado."""
        return self

    def __exit__(self, type, value, traceback):
        """Desconecta-se do arquivo ao receber um exit_code."""
        self.close()

    def __del__(self):
        """Desconecta-se do arquivo ao ser deletado."""
        self.close()


class Cache(SharedMemoryDict):

    u"""
    Classe para guardar dados em RAM para acesso rápido.

    Permite definir um tempo expiração para as chaves.
    """

    def __init__(self, name=None, size=8192, file_location=None, expire=None,
                 force_flush=False):
        u"""
        Conecta-se a chave 'name' ou cria se não houver.

        name: Nome do arquivo que será usado como endereçamento de memória
        size: Quantos caracteres serão alocados na memoria.
        file_location: Onde será guardado o arquivo de endereçamento
        expire: Tempo de expiração padrão das chaves

        São adicionados 5 caracteres ao fim do arquivo para contar os clients.
        """
        super(Cache, self).__init__(name, size, file_location, force_flush)
        self.default_expire = expire

    @classmethod
    def flush_file(cls, file_name, size=8192):
        u"""Limpa o conteúdo de um arquivo a ser usado como file descriptor."""
        f = open(file_name, 'wb')
        f.write("{}%s{}%s00000" % (" " * (size - 2), " " * (size - 2)))
        f.close()
        # os.chmod(file_name, 0777)

    def _expiration_data(self):
        u"""Retorna o json de tempos de expiração."""
        self.mm.seek(self.size)
        return self.mm.read(self.size)

    def __getattr__(self, attr):
        """Getter."""
        if attr == 'connected_clients':
            self.mm.seek(self.size * 2)
            return int(self.mm.read(5))
        # else:
        #     return super(Cache, self).__getattr__(attr)

    def __setattr__(self, attr, value):
        """Setter."""
        if attr == 'connected_clients':
            value = '%05d' % value
            self.mm.seek(self.size * 2)
            self.mm.write(value)
        else:
            return super(Cache, self).__setattr__(attr, value)

    def get_dict(self):
        u"""
        Retorna o conteúdo da memória em um dict.

        Também verifica se existem chaves expiradas e as remove.
        """
        data = json.loads(self._dump_data())
        expiration_data = self.get_expiration_dict()
        updated = False
        for key in data.keys():
            expiration = expiration_data.get(key)
            if expiration and now_seconds() >= expiration:
                data.pop(key)
                expiration_data.pop(key)
                updated = True
        if updated:
            self.write(data)
            self.write_expiration(expiration_data)
        return data

    def get_expiration_dict(self):
        u"""Retorna o dicionario de tempos de expiração."""
        data = self._expiration_data()
        return json.loads(data)

    def delete(self, key):
        """Remove uma chave."""
        whole_data = self.get_dict()
        whole_data.pop(key)
        self.write(whole_data)
        self.set_expiration(key, None)

    def get_expiration(self, key):
        u"""Verifica a expiração de uma dada chave."""
        return self.get_expiration_dict().get(key, None)

    def set_expiration(self, key, expiration):
        u"""Seta o tempo de expiração para uma chave."""
        whole_expiration_data = self.get_expiration_dict()
        if not expiration and key in whole_expiration_data:
            whole_expiration_data.pop(key)
        else:
            whole_expiration_data[key] = now_seconds() + expiration
        self.write_expiration(whole_expiration_data)

    def write_expiration(self, dict_data):
        u"""Escreve os dados de expiração na memória."""
        self._flush_expiration()
        json_string = json.dumps(dict_data)
        self.mm.write(json_string)

    def _flush_data(self):
        u"""Limpa o conteúdo da memória."""
        self.mm.seek(0)
        self.mm.write("{}%s" % (" " * (self.size - 2), ))
        self.mm.seek(0)

    def _flush_expiration(self):
        u"""Limpa os dados de expiracão da memória."""
        self.mm.seek(self.size)
        self.mm.write("{}%s" % (" " * (self.size - 2), ))
        self.mm.seek(self.size)

    def _flush_memory(self):
        u"""Limpa todo o conteúdo e dados de expiração da memória."""
        self.mm.seek(0)
        self.mm.write("{}%s{}%s" % (" " * (self.size - 2), ) * 2)
        self.mm.seek(0)

    def __setitem__(self, key, value):
        u"""
        Permite escrever um valor da memória usando uma chave.

        Define a expiração padrão, se houver.

        Ex:
        >>> obj = SharedMemoryDict(name='foo')
        >>> obj['bar'] = 'Hello World'
        """
        super(Cache, self).__setitem__(key, value)
        if self.default_expire:
            self.set_expiration(key, self.default_expire)
