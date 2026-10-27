# Resultados das Questões de Competência - OntoLearn v2.1

Arquivos de entrada (MD5):

- ABox de referência / declarado: `base_referencia.owl` - 109b1234768f1a3f6680a070efed18c3 - 791 triplas
- ABox de referência / inferido: `base_referencia_inferida.owl` - 49eecdc545ae742faf22d47f796c340d - 869 triplas
- base ampliada / declarado: `base_ampliada.owl` - 5f4676c27941c17bcee9e949350cad05 - 1017 triplas
- base ampliada / inferido: `base_ampliada_inferida.owl` - 1f7ca12fab22779df629e1b5ce42e6e4 - 1240 triplas

## QC1-a (qc1.rq, ABox de referência)
Parâmetros: {'aprendiz': 'João Silva'}
- Esperado (1): [('Herança em Python',)]
- Declarado (1): [('Herança em Python',)] -> confere
- Inferido  (1): [('Herança em Python',)] -> confere

## QC1-b (qc1.rq, base ampliada)
Parâmetros: {'aprendiz': 'Carlos Menezes'}
- Esperado (2): [('Classes e Objetos em POO',), ('Tipos de Dados e Variáveis em Python',)]
- Declarado (1): [('Classes e Objetos em POO',)] -> confere
- Inferido  (2): [('Classes e Objetos em POO',), ('Tipos de Dados e Variáveis em Python',)] -> confere

## QC1-c (qc1.rq, base ampliada)
Parâmetros: {'aprendiz': 'Luiza Prado'}
- Esperado (0): []
- Declarado (0): [] -> confere
- Inferido  (0): [] -> confere

## QC2-a (qc2.rq, ABox de referência)
Parâmetros: {'aprendiz': 'João Silva', 'competencia': 'Herança em Python'}
- Esperado (2): [('Aplicar', 'QUEST-0003'), ('Lembrar', 'QUEST-0005')]
- Declarado (2): [('Aplicar', 'QUEST-0003'), ('Lembrar', 'QUEST-0005')] -> confere
- Inferido  (2): [('Aplicar', 'QUEST-0003'), ('Lembrar', 'QUEST-0005')] -> confere

## QC2-b (qc2.rq, base ampliada)
Parâmetros: {'aprendiz': 'Ana Beatriz Rocha', 'competencia': 'Polimorfismo em Python'}
- Esperado (2): [('Analisar', 'QUEST-0007'), ('Aplicar', 'QUEST-0006')]
- Declarado (2): [('Analisar', 'QUEST-0007'), ('Aplicar', 'QUEST-0006')] -> confere
- Inferido  (2): [('Analisar', 'QUEST-0007'), ('Aplicar', 'QUEST-0006')] -> confere

## QC3-a (qc3.rq, ABox de referência)
Parâmetros: {'competencia': 'Classes e Objetos em POO'}
- Esperado (1): [('AVAL-0002', 'QUEST-0001')]
- Declarado (1): [('AVAL-0002', 'QUEST-0001')] -> confere
- Inferido  (1): [('AVAL-0002', 'QUEST-0001')] -> confere

## QC3-b (qc3.rq, ABox de referência)
Parâmetros: {'competencia': 'Herança em Python'}
- Esperado (2): [('AVAL-0002', 'QUEST-0003'), ('AVAL-0002', 'QUEST-0005')]
- Declarado (1): [('AVAL-0002', 'QUEST-0005')] -> confere
- Inferido  (2): [('AVAL-0002', 'QUEST-0003'), ('AVAL-0002', 'QUEST-0005')] -> confere

## QC3-c (qc3.rq, base ampliada)
Parâmetros: {'competencia': 'Herança em Python'}
- Esperado (3): [('AVAL-0002', 'QUEST-0003'), ('AVAL-0002', 'QUEST-0005'), ('AVAL-0003', 'QUEST-0006')]
- Declarado (2): [('AVAL-0002', 'QUEST-0005'), ('AVAL-0003', 'QUEST-0006')] -> confere
- Inferido  (3): [('AVAL-0002', 'QUEST-0003'), ('AVAL-0002', 'QUEST-0005'), ('AVAL-0003', 'QUEST-0006')] -> confere

## QC4-a (qc4_caminho.rq, ABox de referência)
Parâmetros: {'competencia': 'Herança em Python'}
- Esperado (1): [('Classes e Objetos em POO',)]
- Declarado (1): [('Classes e Objetos em POO',)] -> confere
- Inferido  (1): [('Classes e Objetos em POO',)] -> confere

## QC4-b (qc4_caminho.rq, base ampliada)
Parâmetros: {'competencia': 'Polimorfismo em Python'}
- Esperado (3): [('Classes e Objetos em POO',), ('Herança em Python',), ('Tipos de Dados e Variáveis em Python',)]
- Declarado (3): [('Classes e Objetos em POO',), ('Herança em Python',), ('Tipos de Dados e Variáveis em Python',)] -> confere
- Inferido  (3): [('Classes e Objetos em POO',), ('Herança em Python',), ('Tipos de Dados e Variáveis em Python',)] -> confere

## QC4-c (qc4_direta.rq, base ampliada)
Parâmetros: {'competencia': 'Polimorfismo em Python'}
- Esperado (3): [('Classes e Objetos em POO',), ('Herança em Python',), ('Tipos de Dados e Variáveis em Python',)]
- Declarado (1): [('Herança em Python',)] -> confere
- Inferido  (3): [('Classes e Objetos em POO',), ('Herança em Python',), ('Tipos de Dados e Variáveis em Python',)] -> confere

## QC5-a (qc5.rq, ABox de referência)
Parâmetros: {'competencia': 'Herança em Python'}
- Esperado (1): [('REC-0004', 'http://example.com/heranca-python-video')]
- Declarado (1): [('REC-0004', 'http://example.com/heranca-python-video')] -> confere
- Inferido  (1): [('REC-0004', 'http://example.com/heranca-python-video')] -> confere

## QC5-b (qc5.rq, base ampliada)
Parâmetros: {'competencia': 'Classes e Objetos em POO'}
- Esperado (2): [('REC-0002', 'http://ontolearn.com/aula1-poo'), ('REC-0008', 'https://example.org/ontolearn/video-classes-objetos')]
- Declarado (1): [('REC-0002', 'http://ontolearn.com/aula1-poo')] -> confere
- Inferido  (2): [('REC-0002', 'http://ontolearn.com/aula1-poo'), ('REC-0008', 'https://example.org/ontolearn/video-classes-objetos')] -> confere

## QC6-a (qc6.rq, ABox de referência)
Parâmetros: {'nivel': 'Aplicar', 'area': 'Programação'}
- Esperado (1): [('João Silva',)]
- Declarado (1): [('João Silva',)] -> confere
- Inferido  (1): [('João Silva',)] -> confere

## QC6-b (qc6.rq, base ampliada)
Parâmetros: {'nivel': 'Aplicar', 'area': 'Programação'}
- Esperado (3): [('Ana Beatriz Rocha',), ('Carlos Menezes',), ('João Silva',)]
- Declarado (2): [('Ana Beatriz Rocha',), ('João Silva',)] -> confere
- Inferido  (3): [('Ana Beatriz Rocha',), ('Carlos Menezes',), ('João Silva',)] -> confere

## QC7-a (qc7.rq, ABox de referência)
Parâmetros: {'aprendiz': 'João Silva', 'competencia': 'Herança em Python'}
- Esperado (0): []
- Declarado (0): [] -> confere
- Inferido  (0): [] -> confere
- Nota: Lacuna de dados na ABox original: os recursos do histórico (REC-0002, REC-0005) não estão vinculados a competências.

## QC7-b (qc7.rq, base ampliada)
Parâmetros: {'aprendiz': 'João Silva', 'competencia': 'Herança em Python'}
- Esperado (1): [('http://ontolearn.com/exercicios-heranca',)]
- Declarado (1): [('http://ontolearn.com/exercicios-heranca',)] -> confere
- Inferido  (1): [('http://ontolearn.com/exercicios-heranca',)] -> confere

## QC7-c (qc7.rq, base ampliada)
Parâmetros: {'aprendiz': 'Carlos Menezes', 'competencia': 'Classes e Objetos em POO'}
- Esperado (1): [('https://example.org/ontolearn/video-classes-objetos',)]
- Declarado (0): [] -> confere
- Inferido  (1): [('https://example.org/ontolearn/video-classes-objetos',)] -> confere

## QC8-a (qc8.rq, ABox de referência)
Parâmetros: {}
- Esperado (1): [('João Silva', 'Herança em Python', 'Aplicar', 'Lembrar', '2')]
- Declarado (1): [('João Silva', 'Herança em Python', 'Aplicar', 'Lembrar', '2')] -> confere
- Inferido  (1): [('João Silva', 'Herança em Python', 'Aplicar', 'Lembrar', '2')] -> confere

## QC8-b (qc8.rq, base ampliada)
Parâmetros: {}
- Esperado (2): [('Ana Beatriz Rocha', 'Polimorfismo em Python', 'Aplicar', 'Analisar', '-1'), ('João Silva', 'Herança em Python', 'Aplicar', 'Lembrar', '2')]
- Declarado (2): [('Ana Beatriz Rocha', 'Polimorfismo em Python', 'Aplicar', 'Analisar', '-1'), ('João Silva', 'Herança em Python', 'Aplicar', 'Lembrar', '2')] -> confere
- Inferido  (2): [('Ana Beatriz Rocha', 'Polimorfismo em Python', 'Aplicar', 'Analisar', '-1'), ('João Silva', 'Herança em Python', 'Aplicar', 'Lembrar', '2')] -> confere
