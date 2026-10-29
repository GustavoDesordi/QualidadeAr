# Luiz - integracao com Redis e consulta dos Hashes.
from datetime import datetime, timezone
import unicodedata
import redis


def conectar():
    cache = redis.Redis.from_url('redis://localhost:6379/0',
                                decode_responses=True, socket_connect_timeout=3,
                                socket_timeout=3)
    cache.ping()
    return cache


def chave(resumo):
    if 'sensor_id' in resumo:
        return 'qualidadear:sensor:' + resumo['sensor_id']
    cidade = unicodedata.normalize('NFKD', resumo['cidade'])
    cidade = ''.join(c for c in cidade if not unicodedata.combining(c)).lower()
    return 'qualidadear:cidade:%s:%s' % (resumo['uf'], cidade)


def salvar(cache, resumos):
    recentes = {}
    for resumo in resumos:
        nome = chave(resumo)
        if nome not in recentes or resumo['fim_periodo'] > recentes[nome]['fim_periodo']:
            recentes[nome] = resumo
    for nome, resumo in recentes.items():
        campos = {}
        for campo, valor in resumo.items():
            if isinstance(valor, datetime):
                valor = valor.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
            campos[campo] = str(valor)
        cache.hset(nome, mapping=campos)
    return list(recentes)


def consultar(cache, nome):
    return cache.hgetall(nome)
