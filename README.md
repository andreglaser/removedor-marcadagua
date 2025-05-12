# Removedor de Marca d'água

Esta API permite remover a marca d'água com o texto "ESSA EMISSÃO FOI LOCALIZADA PELA EQUIPE DE ESPECIALISTAS DO @ALERTADEVOOS" de imagens de passagens aéreas.

## Funcionalidades

- Remoção automática da marca d'água vermelha
- Interface web para upload de imagens
- API para integração com outros sistemas
- Suporte para processamento via URL da imagem
- Upload automático para o ImgBB para obter URLs diretas das imagens processadas

## Como usar

### Interface Web

Acesse a interface web e você pode:
1. Fazer upload de uma imagem diretamente
2. Fornecer a URL de uma imagem para processamento
3. Escolher se deseja fazer upload da imagem processada para o ImgBB

### API

Você pode usar a API diretamente:

```
POST /api/remove-watermark
Content-Type: application/json

{
    "url": "https://exemplo.com/imagem.jpg",
    "upload_to_imgbb": true  // opcional, padrão é true
}
```

A resposta quando `upload_to_imgbb=true` será:

```json
{
    "success": true,
    "url": "https://i.ibb.co/exemplo/imagem.png",
    "display_url": "https://i.ibb.co/exemplo/imagem.png"
}
```

A resposta quando `upload_to_imgbb=false` será:

```json
{
    "success": true,
    "image": "base64_encoded_image_data"
}
```

## Instalação Local

1. Clone o repositório
2. Instale as dependências: `pip install -r requirements.txt`
3. Execute a aplicação: `python app.py`
4. Acesse http://localhost:5000

## Implantação

Esta aplicação está configurada para ser implantada no Render.

### Passos para implantação no Render

1. Faça fork deste repositório para sua conta do GitHub
2. Acesse o [Render](https://render.com/) e crie uma conta ou faça login
3. Clique em "New Web Service"
4. Conecte sua conta do GitHub e selecione este repositório
5. Configure o serviço:
   - Nome: escolha um nome para seu serviço
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
6. Clique em "Create Web Service"

## Tecnologias Utilizadas

- Python
- Flask
- OpenCV
- Pillow
- NumPy
- HTML/CSS/JavaScript
- ImgBB API para hospedagem de imagens