import os
import cv2
import numpy as np
from PIL import Image
import requests
import base64
import logging
import traceback
import json
import sys
from io import BytesIO
from flask import Flask, request, jsonify, render_template, send_file, redirect
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('watermark-remover')

load_dotenv()

# Chave da API do ImgBB
IMGBB_API_KEY = os.environ.get('IMGBB_API_KEY', '755ab7dc4f57880bb1322fca5b572c57')
logger.info(f"IMGBB_API_KEY configurada: {'*****' + IMGBB_API_KEY[-4:] if IMGBB_API_KEY else 'Nu00e3o configurada'}")

app = Flask(__name__)

# Texto da marca d'u00e1gua a ser removida
WATERMARK_TEXT = "ESSA EMISSu00c3O FOI LOCALIZADA PELA EQUIPE DE ESPECIALISTAS DO @ALERTADEVOOS"

# Funu00e7u00e3o para remover a marca d'u00e1gua
def remove_watermark(image):
    logger.info(f"Iniciando remou00e7u00e3o de marca d'u00e1gua. Tamanho da imagem: {image.width}x{image.height}")
    try:
        # Converter a imagem para o formato OpenCV
        img_np = np.array(image)
        img_cv = cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
        original_img = img_cv.copy()  # Guardar uma cu00f3pia da imagem original
        
        # Converter para HSV para facilitar a detecu00e7u00e3o da cor vermelha
        hsv = cv2.cvtColor(img_cv, cv2.COLOR_BGR2HSV)
        
        # Definir faixa para a cor vermelha (a marca d'u00e1gua u00e9 vermelha)
        # Vermelho em HSV pode estar em dois intervalos
        # Ampliando a faixa para capturar mais tons de vermelho
        lower_red1 = np.array([0, 30, 30])  # Valores mais baixos para capturar mais tons
        upper_red1 = np.array([15, 255, 255])
        lower_red2 = np.array([160, 30, 30])  # Valores mais baixos para capturar mais tons
        upper_red2 = np.array([180, 255, 255])
        
        # Criar mu00e1scaras para as duas faixas de vermelho
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        
        # Combinar as mu00e1scaras
        mask = mask1 + mask2
        
        # Aplicar operau00e7u00f5es morfolu00f3gicas para melhorar a mu00e1scara
        kernel = np.ones((5,5), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=2)  # Dilatar para expandir a u00e1rea vermelha
        
        # Encontrar contornos na mu00e1scara
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        logger.info(f"Encontrados {len(contours)} contornos na imagem")
        
        # Variu00e1vel para rastrear se alguma marca d'u00e1gua foi encontrada
        watermark_found = False
        
        # ETAPA 1: Remover as bordas vermelhas laterais
        # Analisar as bordas laterais para verificar se contêm a marca d'água vermelha
        height, width = img_cv.shape[:2]
        
        # Verificar a borda esquerda
        left_border_width = 10  # Largura da borda a ser analisada
        left_border = mask[:, :left_border_width]
        left_red_pixels = np.sum(left_border > 0)
        left_red_ratio = left_red_pixels / (height * left_border_width) if height * left_border_width > 0 else 0
        
        # Verificar a borda direita
        right_border_width = 10  # Largura da borda a ser analisada
        right_border = mask[:, -right_border_width:]
        right_red_pixels = np.sum(right_border > 0)
        right_red_ratio = right_red_pixels / (height * right_border_width) if height * right_border_width > 0 else 0
        
        logger.info(f"Proporção de pixels vermelhos: borda esquerda={left_red_ratio:.4f}, borda direita={right_red_ratio:.4f}")
        
        # Se as bordas tiverem uma alta proporção de pixels vermelhos, remover apenas as bordas
        if left_red_ratio > 0.3 or right_red_ratio > 0.3:
            logger.info("Detectadas bordas vermelhas laterais")
            
            # Encontrar a largura exata das bordas vermelhas
            left_edge = 0
            right_edge = width - 1
            
            # Encontrar onde termina a borda vermelha esquerda
            if left_red_ratio > 0.3:
                for x in range(width // 8):  # Verificar até 1/8 da largura da imagem
                    col_mask = mask[:, x]
                    if np.sum(col_mask > 0) / height < 0.1:  # Se menos de 10% dos pixels são vermelhos
                        left_edge = x
                        break
            
            # Encontrar onde começa a borda vermelha direita
            if right_red_ratio > 0.3:
                for x in range(width - 1, width - width // 8, -1):  # Verificar até 1/8 da largura da imagem
                    col_mask = mask[:, x]
                    if np.sum(col_mask > 0) / height < 0.1:  # Se menos de 10% dos pixels são vermelhos
                        right_edge = x
                        break
            
            logger.info(f"Bordas vermelhas detectadas: esquerda={left_edge}, direita={right_edge}")
            
            # Criar uma nova imagem sem as bordas vermelhas
            if left_edge > 0 or right_edge < width - 1:
                # Recortar a imagem para remover as bordas vermelhas
                img_cv = original_img[:, left_edge:right_edge+1]
                logger.info(f"Imagem recortada para remover bordas vermelhas. Nova largura: {right_edge-left_edge+1}")
                watermark_found = True
        
        # ETAPA 2: Procurar por contornos que possam ser a marca d'u00e1gua horizontal
        if contours:
            # Ordenar contornos por u00e1rea (do maior para o menor)
            contours = sorted(contours, key=cv2.contourArea, reverse=True)
            
            for i, contour in enumerate(contours[:5]):  # Verificar apenas os 5 maiores contornos
                # Obter o retu00e2ngulo que envolve o contorno
                x, y, w, h = cv2.boundingRect(contour)
                
                # Calcular a razu00e3o largura/altura
                aspect_ratio = float(w) / h if h > 0 else 0
                
                # Se o retu00e2ngulo for largo e fino (razu00e3o alta), provavelmente u00e9 a marca d'u00e1gua horizontal
                # Tambu00e9m verificamos se a largura u00e9 significativa em relau00e7u00e3o u00e0 largura da imagem
                if aspect_ratio > 5 and w > img_cv.shape[1] * 0.5 and h < img_cv.shape[0] * 0.2:
                    logger.info(f"Contorno {i+1} identificado como marca d'u00e1gua horizontal: x={x}, y={y}, w={w}, h={h}, aspect_ratio={aspect_ratio:.2f}")
                    
                    # Criar uma mu00e1scara para esta regiu00e3o
                    region_mask = np.zeros((img_cv.shape[0], img_cv.shape[1]), dtype=np.uint8)
                    cv2.drawContours(region_mask, [contour], 0, 255, -1)
                    
                    # Preencher a regiu00e3o com a cor do fundo (branco neste caso)
                    img_cv[region_mask == 255] = [255, 255, 255]
                    logger.info("Marca d'u00e1gua horizontal removida com sucesso")
                    watermark_found = True
                    break
                else:
                    logger.debug(f"Contorno {i+1} nu00e3o u00e9 marca d'u00e1gua horizontal: x={x}, y={y}, w={w}, h={h}, aspect_ratio={aspect_ratio:.2f}")
        
        if not watermark_found:
            logger.warning("Nenhuma marca d'u00e1gua detectada na imagem.")
        
        # Converter de volta para RGB
        result_img = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)
        return Image.fromarray(result_img)
    except Exception as e:
        logger.error(f"Erro ao remover marca d'u00e1gua: {str(e)}")
        logger.error(traceback.format_exc())
        raise

# Funu00e7u00e3o para fazer upload de imagem para o ImgBB
def upload_to_imgbb(image):
    logger.info("Iniciando upload para o ImgBB")
    try:
        # Salvar a imagem em um buffer
        buffer = BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)
        
        # Converter para base64
        img_str = base64.b64encode(buffer.getvalue())
        logger.debug(f"Imagem convertida para base64. Tamanho: {len(img_str)} bytes")
        
        # Fazer upload para o ImgBB
        url = "https://api.imgbb.com/1/upload"
        payload = {
            "key": IMGBB_API_KEY,
            "image": img_str,
            "name": "processed_image",
        }
        
        logger.info("Enviando requisiu00e7u00e3o para o ImgBB API")
        response = requests.post(url, payload)
        logger.debug(f"Resposta do ImgBB - Status: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"Erro na resposta do ImgBB: {response.text}")
            raise Exception(f"ImgBB API retornou status {response.status_code}: {response.text}")
        
        try:
            data = response.json()
            logger.debug(f"Resposta JSON do ImgBB: {json.dumps(data)}")
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON da resposta: {str(e)}")
            logger.error(f"Conteu00fado da resposta: {response.text}")
            raise Exception(f"Erro ao decodificar resposta do ImgBB: {str(e)}")
        
        if data.get("success"):
            logger.info(f"Upload para ImgBB bem-sucedido. URL: {data['data']['url']}")
            return data["data"]["url"], data["data"]["display_url"]
        else:
            logger.error(f"Falha no upload para ImgBB: {json.dumps(data)}")
            raise Exception("Falha ao fazer upload para o ImgBB: " + str(data))
    except Exception as e:
        logger.error(f"Erro no upload para ImgBB: {str(e)}")
        logger.error(traceback.format_exc())
        raise

@app.route('/')
def index():
    logger.info("Acesso u00e0 pu00e1gina inicial")
    return render_template('index.html')

@app.route('/remove-watermark', methods=['POST'])
def process_image():
    logger.info(f"Recebida requisiu00e7u00e3o para remover marca d'u00e1gua. Content-Type: {request.content_type}")
    try:
        upload_to_imgbb_enabled = request.form.get('upload_to_imgbb') == 'true'
        logger.info(f"Upload para ImgBB habilitado: {upload_to_imgbb_enabled}")
        
        if 'image' in request.files:
            logger.info("Processando upload de arquivo")
            # Processar upload de arquivo
            file = request.files['image']
            logger.info(f"Arquivo recebido: {file.filename}, Content-Type: {file.content_type}")
            
            try:
                img = Image.open(file)
                logger.info(f"Imagem aberta com sucesso. Tamanho: {img.width}x{img.height}, Formato: {img.format}")
                processed_img = remove_watermark(img)
                
                if upload_to_imgbb_enabled:
                    try:
                        # Fazer upload para o ImgBB
                        url, display_url = upload_to_imgbb(processed_img)
                        response_data = {
                            'success': True,
                            'url': url,
                            'display_url': display_url
                        }
                        logger.info(f"Retornando resposta de sucesso com URL: {url}")
                        return jsonify(response_data)
                    except Exception as e:
                        logger.error(f"Erro ao fazer upload para ImgBB: {str(e)}")
                        return jsonify({'error': str(e)}), 500
                else:
                    # Salvar a imagem processada temporariamente
                    logger.info("Preparando imagem para download direto")
                    output = BytesIO()
                    processed_img.save(output, format='PNG')
                    output.seek(0)
                    
                    logger.info("Enviando arquivo para download")
                    return send_file(output, mimetype='image/png', as_attachment=True, download_name='processed_image.png')
            except Exception as e:
                logger.error(f"Erro ao processar imagem: {str(e)}")
                logger.error(traceback.format_exc())
                return jsonify({'error': f"Erro ao processar imagem: {str(e)}"}), 500
        
        elif request.is_json and 'url' in request.json:
            logger.info("Processando URL da imagem")
            # Processar URL da imagem
            image_url = request.json['url']
            logger.info(f"URL da imagem: {image_url}")
            upload_to_imgbb_enabled = request.json.get('upload_to_imgbb', False)
            logger.info(f"Upload para ImgBB habilitado: {upload_to_imgbb_enabled}")
            
            try:
                logger.info("Baixando imagem da URL")
                response = requests.get(image_url)
                if response.status_code != 200:
                    logger.error(f"Erro ao baixar imagem. Status: {response.status_code}, Resposta: {response.text}")
                    return jsonify({'error': f"Erro ao baixar imagem. Status: {response.status_code}"}), 500
                
                logger.info("Imagem baixada com sucesso")
                img = Image.open(BytesIO(response.content))
                logger.info(f"Imagem aberta com sucesso. Tamanho: {img.width}x{img.height}, Formato: {img.format}")
                processed_img = remove_watermark(img)
                
                if upload_to_imgbb_enabled:
                    try:
                        # Fazer upload para o ImgBB
                        url, display_url = upload_to_imgbb(processed_img)
                        response_data = {
                            'success': True,
                            'url': url,
                            'display_url': display_url
                        }
                        logger.info(f"Retornando resposta de sucesso com URL: {url}")
                        return jsonify(response_data)
                    except Exception as e:
                        logger.error(f"Erro ao fazer upload para ImgBB: {str(e)}")
                        return jsonify({'error': str(e)}), 500
                else:
                    # Salvar a imagem processada temporariamente
                    logger.info("Preparando imagem para retorno em base64")
                    output = BytesIO()
                    processed_img.save(output, format='PNG')
                    output.seek(0)
                    
                    # Converter para base64 para retornar como JSON
                    img_str = base64.b64encode(output.getvalue()).decode('utf-8')
                    logger.info(f"Imagem convertida para base64. Tamanho: {len(img_str)} caracteres")
                    
                    return jsonify({
                        'success': True,
                        'image': img_str
                    })
            except Exception as e:
                logger.error(f"Erro ao processar imagem da URL: {str(e)}")
                logger.error(traceback.format_exc())
                return jsonify({'error': f"Erro ao processar imagem da URL: {str(e)}"}), 500
        else:
            logger.warning("Requisiu00e7u00e3o invu00e1lida: nem arquivo nem URL fornecidos")
            logger.debug(f"Form data: {request.form}")
            logger.debug(f"JSON data: {request.get_json(silent=True)}")
            logger.debug(f"Files: {request.files}")
            return jsonify({'error': 'No image provided'}), 400
    except Exception as e:
        logger.error(f"Erro nu00e3o tratado: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f"Erro interno do servidor: {str(e)}"}), 500

@app.route('/api/remove-watermark', methods=['POST'])
def api_remove_watermark():
    logger.info("Recebida requisiu00e7u00e3o para API remove-watermark")
    if not request.is_json:
        logger.warning(f"Requisiu00e7u00e3o invu00e1lida: nu00e3o u00e9 JSON. Content-Type: {request.content_type}")
        return jsonify({'error': 'Request must be JSON'}), 400
        
    if 'url' not in request.json:
        logger.warning("Requisiu00e7u00e3o invu00e1lida: URL da imagem nu00e3o fornecida")
        return jsonify({'error': 'Image URL is required'}), 400
    
    # Verificar se deve fazer upload para o ImgBB
    upload_to_imgbb_enabled = request.json.get('upload_to_imgbb', True)
    logger.info(f"Upload para ImgBB habilitado: {upload_to_imgbb_enabled}")
    
    try:
        # Obter a imagem da URL
        image_url = request.json['url']
        logger.info(f"URL da imagem: {image_url}")
        
        logger.info("Baixando imagem da URL")
        response = requests.get(image_url)
        if response.status_code != 200:
            logger.error(f"Erro ao baixar imagem. Status: {response.status_code}")
            return jsonify({'error': f"Erro ao baixar imagem. Status: {response.status_code}"}), 500
        
        logger.info("Imagem baixada com sucesso")
        img = Image.open(BytesIO(response.content))
        logger.info(f"Imagem aberta com sucesso. Tamanho: {img.width}x{img.height}, Formato: {img.format}")
        
        # Processar a imagem
        processed_img = remove_watermark(img)
        
        if upload_to_imgbb_enabled:
            try:
                # Fazer upload para o ImgBB
                url, display_url = upload_to_imgbb(processed_img)
                response_data = {
                    'success': True,
                    'url': url,
                    'display_url': display_url
                }
                logger.info(f"Retornando resposta de sucesso com URL: {url}")
                return jsonify(response_data)
            except Exception as e:
                logger.error(f"Erro ao fazer upload para ImgBB: {str(e)}")
                return jsonify({'error': str(e)}), 500
        else:
            # Salvar a imagem processada temporariamente
            logger.info("Preparando imagem para retorno em base64")
            output = BytesIO()
            processed_img.save(output, format='PNG')
            output.seek(0)
            
            # Converter para base64 para retornar como JSON
            img_str = base64.b64encode(output.getvalue()).decode('utf-8')
            logger.info(f"Imagem convertida para base64. Tamanho: {len(img_str)} caracteres")
            
            return jsonify({
                'success': True,
                'image': img_str
            })
    except Exception as e:
        logger.error(f"Erro ao processar imagem: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Iniciando servidor na porta {port}")
    app.run(host='0.0.0.0', port=port, debug=False)