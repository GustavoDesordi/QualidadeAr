# Etapa II: testes reais com uma amostra diferente da demonstracao.
from datetime import datetime, timedelta, timezone
from math import isclose
from uuid import uuid4
import banco
import gerador
import consultas
import agregacoes
import redis_service


def main():
    cliente, _ = banco.conectar()
    identificador = uuid4().hex
    nome_banco = 'QualidadeArTeste_' + identificador
    db = cliente[nome_banco]
    cache = None
    chaves = []
    try:
        cache = redis_service.conectar()
        cidade = 'Teste_' + identificador
        s1, s2 = 'T1_' + identificador, 'T2_' + identificador
        db.Sensores.insert_many([
            {'_id': s1, 'localizacao': {'cidade': cidade, 'uf': 'SC'}},
            {'_id': s2, 'localizacao': {'cidade': cidade, 'uf': 'SC'}}])
        inicio = datetime(2030, 1, 1, 10, tzinfo=timezone.utc)
        fim = inicio + timedelta(hours=1)
        dados = []
        # Sensor 1 tem duas leituras; sensor 2 tem uma na primeira hora.
        amostra = [(s1, 0, 10, 20, 400, 20, 50),
                   (s1, 5, 20, 40, 500, 22, 60),
                   (s2, 5, 100, 200, 600, 24, 70),
                   (s1, 60, 30, 60, 550, 23, 65)]
        for sensor, minuto, pm25, pm10, co2, temperatura, umidade in amostra:
            dados.append({'sensor_id': sensor,
                'timestamp': inicio + timedelta(minutes=minuto),
                'pm25': pm25, 'pm10': pm10, 'co2': co2,
                'temperatura': temperatura, 'umidade': umidade})
        db.Medicoes.insert_many(dados)
        leituras = consultas.consultar(db, s1, inicio, fim)
        assert len(leituras) == 2, 'Consulta incluiu a leitura do fim do periodo'
        sensores = agregacoes.resumir(db, inicio, fim, 'sensor')
        cidades = agregacoes.resumir(db, inicio, fim, 'cidade')
        assert len(sensores) == 2 and len(cidades) == 1
        cidade_hora = cidades[0]
        esperado = {'qt_medicoes': 3, 'pm25_media': 130/3,
                    'pm10_media': 260/3, 'co2_media': 500,
                    'temperatura_media': 22, 'umidade_media': 60,
                    'pm25_max': 100, 'pm10_max': 200}
        for campo, valor in esperado.items():
            assert isclose(cidade_hora[campo], valor), campo
        for resumo in sensores:
            if resumo['sensor_id'] == s1:
                assert resumo['qt_medicoes'] == 2
                assert resumo['pm25_media'] == 15 and resumo['pm25_max'] == 20
        assert cidade_hora['inicio_periodo'] == inicio
        assert cidade_hora['fim_periodo'] == fim
        # Inclui a segunda hora para conferir qual resumo fica no Redis.
        limite = fim + timedelta(hours=1)
        todos = agregacoes.resumir(db, inicio, limite, 'sensor')
        todos += agregacoes.resumir(db, inicio, limite, 'cidade')
        for resumo in todos:
            nome = redis_service.chave(resumo)
            if nome not in chaves:
                chaves.append(nome)
        redis_service.salvar(cache, todos)
        assert len(chaves) == 3
        h = redis_service.consultar(cache, 'qualidadear:sensor:' + s1)
        assert float(h['pm25_media']) == 30
        assert h['fim_periodo'] == '2030-01-01T12:00:00Z'
        for nome in chaves:
            assert redis_service.consultar(cache, nome), 'Hash vazio'
        # Confere tambem volume e repeticao da carga do gerador em banco de teste.
        cadastro = banco.cadastrar(db)
        geradas = gerador.gerar(cadastro)
        assert len(cadastro) == 6 and len(geradas) == 1728
        gerador.inserir(db, geradas)
        quantidade = db.Medicoes.count_documents({})
        gerador.inserir(db, geradas)
        assert db.Medicoes.count_documents({}) == quantidade
        print('APROVADO: consulta, fim exclusivo, medias, maximos e contagens.')
        print('APROVADO: media global com quantidades diferentes de leituras.')
        print('APROVADO: HSET/HGETALL e selecao da ultima janela.')
        print('APROVADO: geracao de 1728 leituras e repeticao sem duplicacao.')
    finally:
        # Remove somente o banco e as chaves exclusivos desta execucao de teste.
        if cache is not None:
            for nome in chaves:
                cache.delete(nome)
            cache.close()
        cliente.drop_database(nome_banco)
        cliente.close()


if __name__ == '__main__':
    main()
