"""Teste demonstrativo da Etapa II - QualidadeArTesteGerador.

Executar na raiz do projeto:
    python codigo/testes.py

O script utiliza somente um banco de teste: QualidadeArTesteGerador.
Ele cria 6 sensores e 1.728 medicoes simuladas com seed 30 e periodo em 2030,
para que os dados sejam diferentes da demonstracao principal (seed 42 / 2026).

O banco principal QualidadeAr e suas chaves Redis nao sao alterados.
Os dados do teste permanecem disponiveis no MongoDB Compass apos a execucao.
Para remover somente o banco e as chaves deste teste:
    python codigo/testes.py --limpar
"""

import argparse
import random
from datetime import datetime, timedelta, timezone
from math import isclose
from pprint import pprint

import agregacoes
import banco
import consultas
import gerador
import redis_service


BANCO_TESTE = 'QualidadeArTesteGerador'
SEED_TESTE = 30
INICIO_TESTE = datetime(2030, 1, 1, tzinfo=timezone.utc)
FIM_TESTE = INICIO_TESTE + timedelta(hours=24)
CAMPOS = ['pm25', 'pm10', 'co2', 'temperatura', 'umidade']

# Identificadores e cidades exclusivos evitam colisao com os Hashes da demo.
CIDADES = [
    ('Chapecó - TESTE', -27.1009, -52.6157),
    ('Xanxerê - TESTE', -26.8760, -52.4040),
    ('Concórdia - TESTE', -27.2340, -52.0270),
]


def titulo(texto):
    print('\n' + '=' * 78)
    print(texto)
    print('=' * 78)


def criar_sensores(db):
    """Cria seis sensores de teste, dois em cada cidade."""
    sensores = []
    for i in range(6):
        cidade, latitude, longitude = CIDADES[i // 2]
        sensor = {
            '_id': 'TESTE_S%03d' % (i + 1),
            'modelo': 'AirMonitor-200',
            'descricao': 'Sensor de demonstracao - ' + cidade,
            'localizacao': {
                'cidade': cidade,
                'uf': 'SC',
                'latitude': latitude,
                'longitude': longitude,
            },
            'ativo': True,
            'grandezas': ['PM2.5', 'PM10', 'CO2', 'temperatura', 'umidade'],
        }
        db.Sensores.replace_one({'_id': sensor['_id']}, sensor, upsert=True)
        sensores.append(sensor)

    db.Medicoes.create_index(
        [('sensor_id', 1), ('timestamp', -1)], unique=True
    )
    return sensores


def gerar_medicoes_teste(sensores):
    """Gera 24 horas de dados reprodutiveis com seed diferente da demo."""
    aleatorio = random.Random(SEED_TESTE)
    medicoes = []

    for sensor in sensores:
        for i in range(288):
            medicao = {
                '_id': 'teste:%s:%03d' % (sensor['_id'], i),
                'sensor_id': sensor['_id'],
                'timestamp': INICIO_TESTE + timedelta(minutes=i * 5),
                'pm25': round(aleatorio.uniform(10, 40), 2),
                'pm10': round(aleatorio.uniform(20, 70), 2),
                'co2': aleatorio.randint(400, 700),
                'temperatura': round(aleatorio.uniform(20, 30), 2),
                'umidade': round(aleatorio.uniform(50, 80), 2),
            }
            medicoes.append(medicao)

    return medicoes


def media(documentos, campo):
    return sum(item[campo] for item in documentos) / len(documentos)


def conferir_estatisticas(resumo, documentos):
    """Compara o resumo MongoDB com calculos independentes em Python."""
    assert resumo['qt_medicoes'] == len(documentos)

    for campo in CAMPOS:
        esperado = media(documentos, campo)
        assert isclose(
            resumo[campo + '_media'], esperado,
            rel_tol=1e-9, abs_tol=1e-9,
        ), 'Media divergente: ' + campo

    for campo in ('pm25', 'pm10'):
        esperado = max(item[campo] for item in documentos)
        assert isclose(
            resumo[campo + '_max'], esperado,
            rel_tol=1e-9, abs_tol=1e-9,
        ), 'Maximo divergente: ' + campo


def chaves_redis_teste():
    """Retorna somente as nove chaves pertencentes a este banco de teste."""
    chaves = [
        'qualidadear:sensor:TESTE_S%03d' % i for i in range(1, 7)
    ]
    for cidade, _, _ in CIDADES:
        chaves.append(redis_service.chave({'cidade': cidade, 'uf': 'SC'}))
    return chaves


def limpar(cliente, cache):
    cliente.drop_database(BANCO_TESTE)
    chaves = chaves_redis_teste()
    removidas = cache.delete(*chaves) if chaves else 0
    print('Banco removido:', BANCO_TESTE)
    print('Chaves Redis de teste removidas:', removidas)
    print('Banco principal QualidadeAr e seus Hashes foram preservados.')


def executar_teste(cliente, cache):
    # Recria somente o banco de teste. O banco principal nao e tocado.
    cliente.drop_database(BANCO_TESTE)
    cache.delete(*chaves_redis_teste())
    db = cliente[BANCO_TESTE]

    titulo('1. AMBIENTE DE TESTE')
    print('Banco MongoDB:', BANCO_TESTE)
    print('Banco principal preservado: QualidadeAr')
    print('Seed dos dados de teste:', SEED_TESTE)
    print('Periodo: 01/01/2030 00:00 ate 02/01/2030 00:00 UTC')
    print('Quantidade esperada: 6 sensores e 1.728 medicoes')

    titulo('2. SENSORES CADASTRADOS')
    sensores = criar_sensores(db)
    print('Quantidade de sensores:', len(sensores))
    pprint(sensores)
    assert len(sensores) == 6
    print('\nMongoDB Compass: QualidadeArTesteGerador > Sensores')

    titulo('3. GERACAO E INSERCAO DAS 1.728 MEDICOES')
    medicoes = gerar_medicoes_teste(sensores)
    print('Medicoes geradas:', len(medicoes))
    print('Exemplos de medicoes:')
    pprint(medicoes[:3])

    # Reaproveita a rotina de insercao do gerador original.
    gerador.inserir(db, medicoes)
    total = db.Medicoes.count_documents({})
    print('\nDocumentos gravados no MongoDB:', total)
    print('Quantidade por sensor:')
    for sensor in sensores:
        quantidade = db.Medicoes.count_documents(
            {'sensor_id': sensor['_id']}
        )
        print(' ', sensor['_id'], ':', quantidade)
        assert quantidade == 288

    assert len(medicoes) == 1728
    assert total == 1728
    print('\nMongoDB Compass: QualidadeArTesteGerador > Medicoes')

    titulo('4. CONSULTA POR SENSOR E INTERVALO DE TEMPO')
    inicio_hora = INICIO_TESTE + timedelta(hours=10)
    fim_hora = inicio_hora + timedelta(hours=1)
    sensor_exemplo = 'TESTE_S001'
    leituras_sensor = consultas.consultar(
        db, sensor_exemplo, inicio_hora, fim_hora
    )
    print('Consulta:', sensor_exemplo, '| 01/01/2030, 10h ate 11h UTC')
    print('Quantidade encontrada:', len(leituras_sensor))
    pprint(leituras_sensor[:3])
    assert len(leituras_sensor) == 12
    print('Conferido: 12 leituras; inicio incluso e fim exclusivo.')

    titulo('5. AGREGACOES POR SENSOR E POR CIDADE')
    resumos_sensor = agregacoes.resumir(
        db, INICIO_TESTE, FIM_TESTE, 'sensor'
    )
    resumos_cidade = agregacoes.resumir(
        db, INICIO_TESTE, FIM_TESTE, 'cidade'
    )
    print('Resumos por sensor:', len(resumos_sensor), '(6 x 24 horas)')
    print('Resumos por cidade:', len(resumos_cidade), '(3 x 24 horas)')
    assert len(resumos_sensor) == 144
    assert len(resumos_cidade) == 72

    resumo_sensor = next(
        item for item in resumos_sensor
        if item['sensor_id'] == sensor_exemplo
        and item['inicio_periodo'] == inicio_hora
    )
    print('\nResumo do sensor TESTE_S001, das 10h as 11h:')
    pprint(resumo_sensor)
    conferir_estatisticas(resumo_sensor, leituras_sensor)
    print('Conferencia independente das estatisticas do sensor: CORRETA')

    cidade_exemplo = CIDADES[0][0]
    sensores_cidade = [
        item['_id'] for item in sensores
        if item['localizacao']['cidade'] == cidade_exemplo
    ]
    leituras_cidade = list(db.Medicoes.find({
        'sensor_id': {'$in': sensores_cidade},
        'timestamp': {'$gte': inicio_hora, '$lt': fim_hora},
    }))
    resumo_cidade = next(
        item for item in resumos_cidade
        if item['cidade'] == cidade_exemplo
        and item['inicio_periodo'] == inicio_hora
    )
    print('\nResumo da cidade:', cidade_exemplo)
    print('Sensores considerados:', sensores_cidade)
    print('Quantidade de medicoes:', len(leituras_cidade))
    pprint(resumo_cidade)
    assert len(leituras_cidade) == 24
    conferir_estatisticas(resumo_cidade, leituras_cidade)
    print('Conferencia independente das estatisticas da cidade: CORRETA')

    titulo('6. TESTE DO REDIS: RESUMOS MAIS RECENTES')
    todos_resumos = resumos_sensor + resumos_cidade
    chaves = redis_service.salvar(cache, todos_resumos)
    print('Quantidade de Hashes gravados:', len(chaves))
    print('Chaves de teste no Redis:')
    pprint(sorted(chaves))
    assert len(chaves) == 9

    # O Redis guarda somente o resumo mais recente de cada sensor/cidade.
    # Por isso, a comparacao deve usar a janela 23h-00h, e nao a janela
    # das 10h-11h que foi usada acima para demonstrar as agregacoes.
    resumo_sensor_recente = max(
        (item for item in resumos_sensor
         if item['sensor_id'] == sensor_exemplo),
        key=lambda item: item['fim_periodo'],
    )
    resumo_cidade_recente = max(
        (item for item in resumos_cidade
         if item['cidade'] == cidade_exemplo),
        key=lambda item: item['fim_periodo'],
    )

    chave_sensor = redis_service.chave(resumo_sensor_recente)
    chave_cidade = redis_service.chave(resumo_cidade_recente)
    hash_sensor = redis_service.consultar(cache, chave_sensor)
    hash_cidade = redis_service.consultar(cache, chave_cidade)
    print('\nHGETALL', chave_sensor)
    pprint(hash_sensor)
    print('\nHGETALL', chave_cidade)
    pprint(hash_cidade)
    assert hash_sensor and hash_cidade

    campos_redis = [
        'qt_medicoes', 'pm25_media', 'pm10_media', 'co2_media',
        'temperatura_media', 'umidade_media', 'pm25_max', 'pm10_max',
    ]
    for campo in campos_redis:
        assert isclose(
            float(hash_sensor[campo]), float(resumo_sensor_recente[campo]),
            rel_tol=1e-9, abs_tol=1e-9,
        ), 'Hash do sensor diverge em: ' + campo
        assert isclose(
            float(hash_cidade[campo]), float(resumo_cidade_recente[campo]),
            rel_tol=1e-9, abs_tol=1e-9,
        ), 'Hash da cidade diverge em: ' + campo

    assert hash_sensor['fim_periodo'] == '2030-01-02T00:00:00Z'
    assert hash_cidade['fim_periodo'] == '2030-01-02T00:00:00Z'
    print('Conferido: Redis contem os resumos mais recentes (23h-00h)')
    print('e seus campos numericos correspondem aos resultados do MongoDB.')

    titulo('7. TESTE DE REPETICAO DA CARGA')
    print('Documentos antes da segunda insercao:', total)
    gerador.inserir(db, medicoes)
    total_repetido = db.Medicoes.count_documents({})
    print('Documentos depois da segunda insercao:', total_repetido)
    assert total_repetido == total == 1728
    print('Conferido: a segunda insercao nao duplicou documentos.')

    titulo('8. RESULTADO FINAL')
    print('Banco disponivel no Compass:', BANCO_TESTE)
    print('Sensores:', db.Sensores.count_documents({}))
    print('Medicoes:', db.Medicoes.count_documents({}))
    print('Resumos por sensor:', len(resumos_sensor))
    print('Resumos por cidade:', len(resumos_cidade))
    print('Hashes Redis:', len(chaves))
    print('Banco principal QualidadeAr: PRESERVADO')
    print('\nPara visualizar: MongoDB Compass > QualidadeArTesteGerador')
    print('Para limpar somente este teste: python codigo/testes.py --limpar')


def main():
    parser = argparse.ArgumentParser(
        description='Teste integrado com um unico banco de 1.728 medicoes.'
    )
    parser.add_argument(
        '--limpar', action='store_true',
        help='remove QualidadeArTesteGerador e somente os Hashes deste teste.'
    )
    args = parser.parse_args()

    cliente, _ = banco.conectar()
    cache = None
    try:
        cache = redis_service.conectar()
        if args.limpar:
            limpar(cliente, cache)
        else:
            executar_teste(cliente, cache)
    finally:
        if cache is not None:
            cache.close()
        cliente.close()


if __name__ == '__main__':
    main()
