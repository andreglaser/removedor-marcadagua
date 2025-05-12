#!/bin/bash

# Inicializar repositório Git
git init

# Adicionar todos os arquivos
git add .

# Fazer o primeiro commit
git commit -m "Versão inicial do removedor de marca d'água"

# Instruções para conectar ao GitHub
echo "\nPara conectar ao GitHub, execute os seguintes comandos:\n"
echo "1. Crie um novo repositório no GitHub (não inicialize com README)"
echo "2. Execute os comandos abaixo substituindo YOUR_USERNAME pelo seu nome de usuário do GitHub:\n"
echo "   git remote add origin https://github.com/YOUR_USERNAME/watermark-remover-api.git"
echo "   git branch -M main"
echo "   git push -u origin main\n"
echo "3. Depois de fazer o push para o GitHub, você pode implantar no Render seguindo as instruções no README.md"