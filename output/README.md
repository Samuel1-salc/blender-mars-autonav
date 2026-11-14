# Terreno marciano — três vias

Abra `terreno_marciano.blend`, cena `Marte_Tres_Vias`.

- Malha de análise: `Terreno_Heightmap`, 24 × 16 m, 193 × 129 vértices, 24.576 quadriláteros.
- Passo regular de 0,125 m. Uma única altura por posição XY; transformação identidade.
- Ordem dos vértices: `j * 193 + i`. `x = -12 + i * 0.125`, `y = j * 0.125`. A futura matriz terá forma `(129, 193)`, linhas Y e colunas X, valores Z em metros.
- Grupos `Via_A`, `Via_B`, `Via_C`: faixas de 4 m de largura centradas em X = -8, 0, 8 m, percorridas no sentido +Y.
- Inclinações de 35°, 15°, 5° são médias longitudinais de subida/deslocamento horizontal em 16 m. A rugosidade modifica as inclinações locais; veja `validacao.json` para medições nos eixos centrais.
- São faixas comparativas, não trajetos com um mesmo ponto final. As transições entre faixas também possuem inclinação transversal.
- Displacement analítico determinístico incorporado diretamente às coordenadas Z. Nenhum shader ou modificador é necessário para recuperar o relevo. Alterar `height()` e executar novamente permite regenerar a geometria.
- Materiais de solo e rocha misturados por atributo e ruído procedural, inspirados no tutorial. Nenhuma textura externa.
- Coleção `02_Vias_Guias_Visuais` contém apenas linhas e legendas de apresentação. Não deve entrar na análise de elevação.
- A cena anterior foi preservada no arquivo. Cada execução cria uma nova cena, sem apagar cenas anteriores.

## Reproduzir

```bash
blender --background --python output/criar_terreno.py
```

Renderizar o arquivo produzido:

```bash
blender --background output/terreno_marciano.blend --scene Marte_Tres_Vias --render-frame 1
```

O script salva o projeto e a validação na pasta do próprio script. A renderização pode ser feita também com F12 no Blender. Não foram implementados Sobel, classificação automática ou Machine Learning. Os rótulos de viabilidade correspondem ao cenário solicitado, não a uma avaliação física de um rover específico.
