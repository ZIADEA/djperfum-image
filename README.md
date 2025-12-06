<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DJ Perfum - README</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 40px 20px;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
            animation: fadeIn 0.8s ease-out;
        }
        
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(30px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .header-image {
            width: 100%;
            height: auto;
            display: block;
            animation: slideDown 1s ease-out;
        }
        
        @keyframes slideDown {
            from {
                transform: translateY(-50px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }
        
        .content {
            padding: 40px;
        }
        
        .link-section {
            margin-bottom: 30px;
            padding: 20px;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            border-radius: 12px;
            border-left: 4px solid #667eea;
            transition: all 0.3s ease;
            animation: slideIn 0.6s ease-out backwards;
        }
        
        .link-section:nth-child(1) { animation-delay: 0.1s; }
        .link-section:nth-child(2) { animation-delay: 0.2s; }
        .link-section:nth-child(3) { animation-delay: 0.3s; }
        .link-section:nth-child(4) { animation-delay: 0.4s; }
        .link-section:nth-child(5) { animation-delay: 0.5s; }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateX(-30px);
            }
            to {
                opacity: 1;
                transform: translateX(0);
            }
        }
        
        .link-section:hover {
            transform: translateX(5px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        }
        
        .link-section h3 {
            color: #667eea;
            margin-bottom: 10px;
            font-size: 18px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .link-section p {
            color: #4a5568;
            line-height: 1.6;
            margin-bottom: 8px;
        }
        
        .link-section a {
            color: #764ba2;
            text-decoration: none;
            word-break: break-all;
            transition: color 0.3s ease;
            display: inline-block;
        }
        
        .link-section a:hover {
            color: #667eea;
            transform: scale(1.02);
        }
        
        .icon {
            font-size: 24px;
            animation: bounce 2s infinite;
        }
        
        @keyframes bounce {
            0%, 100% { transform: translateY(0); }
            50% { transform: translateY(-5px); }
        }
        
        .video-links {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
        }
        
        .video-links a {
            padding: 8px 16px;
            background: #667eea;
            color: white !important;
            border-radius: 8px;
            transition: all 0.3s ease;
        }
        
        .video-links a:hover {
            background: #764ba2;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
        }
    </style>
</head>
<body>
    <div class="container">
        <img class="header-image" src="https://github.com/user-attachments/assets/d73e5d7e-158c-4655-9bfc-8d0b4b22a820" alt="DJ Perfum Application">
        
        <div class="content">
            <div class="link-section">
                <h3><span class="icon">🔗</span> Dépôt GitHub</h3>
                <p><a href="https://github.com/ZIADEA/djperfum-image" target="_blank">https://github.com/ZIADEA/djperfum-image</a></p>
            </div>
            
            <div class="link-section">
                <h3><span class="icon">🌐</span> Application en ligne</h3>
                <p><a href="https://djperfum-image-fksnza84rdrvv6b4jyjvwu.streamlit.app/" target="_blank">https://djperfum-image-fksnza84rdrvv6b4jyjvwu.streamlit.app/</a></p>
            </div>
            
            <div class="link-section">
                <h3><span class="icon">💬</span> Chatbot direct</h3>
                <p><a href="https://cdn.botpress.cloud/webchat/v3.3/shareable.html?configUrl=https://files.bpcontent.cloud/2025/10/06/14/20251006143331-TLGNO0TS.json" target="_blank">Accéder au chatbot</a></p>
            </div>
            
            <div class="link-section">
                <h3><span class="icon">📱</span> Instagram Bot</h3>
                <p>Posez vos questions via DM et le bot vous répondra automatiquement.</p>
                <p><a href="https://www.instagram.com/______burna_girl_____/" target="_blank">@______burna_girl_____</a></p>
                <p style="margin-top: 10px; font-style: italic; color: #718096;">Cette intégration Instagram peut aider de réels vendeurs à maintenir une conversation et relation client-to-consumer efficace.</p>
            </div>
            
            <div class="link-section">
                <h3><span class="icon">🎥</span> Vidéo démo explicative</h3>
                <div class="video-links">
                    <a href="https://drive.google.com/drive/folders/1RnHUbsi_COcb36wQoHQ9FBltqdQs604z?usp=sharing" target="_blank">📁 Google Drive</a>
                    <a href="#" style="opacity: 0.5; cursor: not-allowed;">📺 YouTube (à venir)</a>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
