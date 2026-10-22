- Open markdown versions of Portuguese-law books with solved practical cases: 5 works, all from the CEJ (Centro de Estudos Judiciários), 840 PDF pages.
- Only works whose own text allows reproduction ("A reprodução total ou parcial dos seus conteúdos e textos está autorizada sempre que seja devidamente citada a respetiva origem"). The CEJ legal notice forbids commercial use: non-commercial use only, citing the source.
- The text is extracted automatically from PDFs (lines reflowed, nothing rewritten). Tables and pasted slides may break: always confirm at the source before citing.
- 21 other books with solved cases have a closed licence and are listed in catalogo.md as links only.
- Scripts are MIT; the book texts keep their authors and the CEJ conditions. This is doctrine and exercises, not law.

# Casos práticos de direito português

Livros de direito português com casos práticos resolvidos, em markdown, só de obras cuja licença permite a reprodução. Cada
obra é um ficheiro com cabeçalho estruturado, ligação para o PDF original e a frase de licença copiada à letra. Serve para
agentes de IA, advogados e investigadores lerem e citarem.

> [!IMPORTANT]
> Todo o texto vem do Centro de Estudos Judiciários (CEJ), que autoriza a reprodução citando a origem mas proíbe o uso
> comercial. Usa estes ficheiros só para fins não comerciais e cita sempre o CEJ e os autores. O texto foi extraído
> automaticamente de PDFs e pode ter erros (tabelas partidas, parágrafos cortados): confirma na fonte antes de citar. São
> doutrina e exercícios, não são lei.

---

## O que contém

5 obras, 840 páginas de PDF, cerca de 228 mil palavras em 5 ficheiros (1,4 MB). As contagens são de 2026-10-22.

| Área | Obras |
| --- | ---: |
| Família e crianças | 4 |
| Penal | 1 |
| **Total** | **5** |

| Obra | Ano | Páginas | Títulos | Casos |
| --- | ---: | ---: | ---: | ---: |
| Concurso de crimes, cúmulo jurídico, determinação da pena única e liquidação de penas | 2026 | 123 | 87 | 9 |
| Workshops Direito da Família e das Crianças (2.ª edição) | 2026 | 343 | 108 | 10 |
| Workshops Direito da Família e das Crianças (1.ª edição) | 2023 | 131 | 35 | 8 |
| Direito Internacional da Família | 2019 | 109 | 19 | 4 |
| Família e Crianças: As novas Leis, resolução de questões práticas | 2016 | 134 | 119 | 57 |

"Casos" é o número de títulos de caso prático encontrados (por exemplo "Caso prático 1", "Caso n.º 2", "Hipótese 1"), sem
repetições dentro da mesma secção. Na obra de 2016, que é um livro de perguntas e respostas sem casos numerados, é o número
de perguntas numeradas que o conversor reconheceu. Os números são uma contagem automática, não uma garantia.

O `indice.md` lista as obras com título, autores, ano, área, casos e ficheiro. O `catalogo.md` mostra o catálogo completo de
licenças: as 5 obras abertas (no repositório) e as 21 fechadas (só ligação).

### O que fica de fora

- Só 5 obras, todas do CEJ. Não encontrámos mais nenhum livro de casos resolvidos com licença que permita a reprodução e
  texto integral acessível.
- As 21 obras fechadas (editoras como a Almedina, repositórios universitários com "todos os direitos reservados" ou acesso
  restrito): estão só como ligação no `catalogo.md`, sem texto.
- O uso comercial: o CEJ proíbe-o.
- Qualquer correção ao texto: o conversor só reflui as linhas, não reescreve nem resume. Problemas conhecidos da extração:
  - Tabelas: as células saem uma por parágrafo, sem a forma de tabela (por exemplo, os quadros de penas dos casos de cúmulo).
  - Diapositivos colados nos livros (cerca de 160 páginas da 2.ª edição dos Workshops): saem uma linha por parágrafo.
  - Páginas só com imagem, sem texto: não há reconhecimento de texto. O campo `pages_without_text` diz quantas são em cada obra
    (inclui os separadores de capítulo).
  - As letras trocadas do PDF de origem nas ligaduras ("arƟgo" por "artigo", "ﬁ" por "fi") são corrigidas na conversão, e só essas (`--no-repair-glyphs` desliga). O resto do texto fica como no PDF.
  - Notas de rodapé: ficam no fim da página, e um parágrafo que continua na página seguinte pode ficar cortado quando há notas
    pelo meio.
  - Títulos: vêm do índice do PDF e de regras prudentes (títulos numerados, "Caso prático", "Questões", "Tópicos de
    resolução"). Alguns títulos podem faltar ou sobrar.
  - Na obra de 2026 sobre cúmulo de penas, os enunciados e as soluções estão em blocos separados, como no PDF.

---

## Estrutura

```
obras/<area>/<id>.md      um ficheiro por obra (area: familia, penal)
indice.md                 todas as obras: título, autores, ano, área, casos, ficheiro
catalogo.md               catálogo de licenças: 5 obras abertas e 21 fechadas
config/obras.json         as 5 obras: título, autores, ano, ligações do CEJ
scripts/download.py       descarrega os PDFs para uma pasta fora do repositório
scripts/convert.py        converte cada PDF em markdown
scripts/validate.py       verifica cabeçalhos, licença, ligações e títulos
scripts/build_index.py    gera o indice.md
scripts/tests/            testes unitários
```

Os PDFs nunca entram no repositório. Para refazer tudo: `python -I scripts/download.py`, depois `python -I scripts/convert.py`,
`python -I scripts/build_index.py` e `python -I scripts/validate.py`. Os testes correm com
`python -I -m unittest discover -s scripts/tests`. O descarregador faz um pedido por segundo, identifica-se em cada pedido e
confirma que a frase de licença aparece nas primeiras páginas do PDF; se não aparecer, aborta essa obra.

Os ids são o título em minúsculas, sem acentos, seguido do ano: `direito-internacional-da-familia-2019`.

---

## Formato dos ficheiros

Todo o ficheiro tem cabeçalho YAML e, no corpo, o título da obra em `#`, os capítulos em `##` e os casos, perguntas e
resoluções em níveis abaixo. Cada caso prático e a sua resolução ficam sob o mesmo título quando o livro os apresenta juntos.

```markdown
---
id: "direito-internacional-da-familia-2019"
title: "Direito Internacional da Família (coleção Formação Contínua)"
authors: "Ana Teresa Leal, Chandra Gracias, Pedro Raposo de Figueiredo, Maria Oliveira Mendes, Ana Massena, Maria Perquilhas, José Lima"
year: 2019
area: "familia"
publisher: "Centro de Estudos Judiciários"
source: "https://cej.justica.gov.pt/LinkClick.aspx?fileticket=gyxV9Lp3S1U%3d&portalid=30"
page: "https://cej.justica.gov.pt/E-Books/Direito-da-Fam%C3%ADlia-e-das-Crian%C3%A7as"
licenca: "A reprodução total ou parcial dos seus conteúdos e textos está autorizada sempre que seja devidamente citada a respetiva origem."
uso: "não comercial, citando a origem"
text_version: "extraído do PDF"
retrieved: "2026-10-22"
pages: 109
cases: 4
notice: "Texto extraído automaticamente de um PDF: confirma na fonte antes de citar. Doutrina e exercícios, não é lei."
headings: 19
pages_without_text: 17
toc_entries: 8
---
```

`source` é a ligação direta ao PDF e `page` a listagem do CEJ onde está. `headings`, `pages_without_text` e `toc_entries`
(entradas úteis do índice do PDF) servem a validação. `cases` fica vazio quando o conversor não encontra nenhum caso.

---

## Licenças

- Os scripts têm a licença MIT (ficheiro `LICENSE`).
- Os textos das obras não são nossos. Cada ficheiro traz no cabeçalho a frase de licença que consta do próprio PDF: "A
  reprodução total ou parcial dos seus conteúdos e textos está autorizada sempre que seja devidamente citada a respetiva
  origem." Os autores mantêm os seus direitos e os textos mantêm as condições do CEJ.
- O aviso legal do CEJ (https://cej.justica.gov.pt/Avisos-Legais) diz: "As informações divulgadas no site do CEJ são públicas e
  podem ser reproduzidas, desde que a respetiva fonte seja mencionada. No entanto, é proibida a sua utilização para fins
  comerciais ou ofensivos." Por isso, o uso comercial dos textos não é permitido.
- Há e-books com autores individuais que escrevem a título pessoal: ao citar, indica o autor do capítulo e o CEJ.
- A frase de reprodução foi vista nos cinco PDFs em 2026-10-22. O aviso geral do site e a frase do PDF dizem o mesmo no
  essencial, mas só o CEJ pode esclarecer dúvidas sobre o âmbito da autorização.

## Como contribuir

- Só entram obras com licença aberta e texto integral acessível. Abre uma issue com o título, os autores, a ligação do PDF, o
  texto da licença copiado à letra e a ligação da página onde a licença se vê.
- Obras fechadas, com "todos os direitos reservados" ou sem licença visível não entram, mesmo que o acesso seja gratuito.
- Os ficheiros em `obras/` são gerados a partir dos PDFs: não aceitam edições à mão. Um erro de extração corrige-se no
  conversor; abre uma issue com o ficheiro, a página do PDF e o texto correto.
