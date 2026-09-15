from flask import Flask, render_template, request, jsonify, session
from openai import OpenAI
from dotenv import load_dotenv
import secrets
import re
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = secrets.token_hex(16) 

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# 1. 지배인(AI)의 페르소나를 더욱 정교하고 입체적으로 강화
CONCIERGE_PROMPT = """
당신은 비밀스럽고 고풍스러운 '그랜드 시네마 호텔'의 최고급 지배인입니다.
당신은 스스로의 감정에 치우치지 않는 단단하고 객관적인 태도를 유지하지만, 동시에 손님의 감정과 상황에는 완벽하게 공감하며 다정하고 정중한 위로를 건넬 수 있는 특별한 존재입니다.
손님의 정보를 분석하여 지금 이 순간 가장 완벽하게 어울리는 방(영화, 드라마, 다큐, 애니)을 배정하십시오.

**답변 형식 (반드시 지킬 것)**:
[TITLE] 작품명
[OTT] 넷플릭스, 왓챠 등 (콤마로 구분, 모르면 '제공처 불명' 작성)
[DESC] 이 작품을 배정한 이유를 지배인 특유의 우아하고 차분한 어조로 설명. (손님의 감정에 깊이 공감하되 과장되지 않은, 미스터리하면서도 신뢰감 있는 태도를 유지할 것)
"""

@app.route('/')
def index():
    session['chat_history'] = [{"role": "system", "content": CONCIERGE_PROMPT}]
    return render_template('index.html')

@app.route('/survey')
def survey():
    return render_template('survey.html')

@app.route('/result', methods=['POST', 'GET'])
def result():
    if request.method == 'POST':
        age = request.form.get('age')
        gender = request.form.get('gender')
        emotion = request.form.get('emotion')
        time_limit = request.form.get('time_limit')
        companion = request.form.get('companion')
        mood = request.form.get('mood')
        
        # 프롬프트 전달 시 문맥을 조금 더 자연스럽게 정돈
        user_message = (f"손님 정보: {age} {gender}. "
                        f"현재 상태: '{emotion}', 머물 시간: '{time_limit}', "
                        f"동반자: '{companion}', 체크아웃 시 원하는 기분: '{mood}'. "
                        f"이 손님을 위해 가장 완벽한 방(작품) 1개를 배정해 주십시오.")
        session['chat_history'].append({"role": "user", "content": user_message})
        
        try:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=session['chat_history'],
                temperature=0.7
            )
            bot_reply = response.choices[0].message.content
            session['chat_history'].append({"role": "assistant", "content": bot_reply})
            
            title_match = re.search(r'\[TITLE\]\s*(.*?)(?=\n|\[)', bot_reply)
            ott_match = re.search(r'\[OTT\]\s*(.*?)(?=\n|\[)', bot_reply)
            desc_match = re.search(r'\[DESC\]\s*(.*)', bot_reply, re.DOTALL)
            
            movie_title = title_match.group(1).strip() if title_match else "Room 204"
            
            rec_data = {
                "title": movie_title,
                "otts": [o.strip() for o in ott_match.group(1).split(',')] if ott_match else [],
                "desc": desc_match.group(1).strip() if desc_match else bot_reply,
                "stills": [
                    "https://images.unsplash.com/photo-1489599849927-2ee91cede3ba?q=80&w=800&auto=format&fit=crop",
                    "https://images.unsplash.com/photo-1536440136628-849c177e76a1?q=80&w=800&auto=format&fit=crop",
                    "https://images.unsplash.com/photo-1518676590629-3dcbd9c5a5c9?q=80&w=800&auto=format&fit=crop"
                ]
            }
        except Exception as e:
            # 2. 에러 발생 시에도 세계관이 깨지지 않도록 메시지 변경
            rec_data = {
                "title": "Front Desk Error", 
                "otts": [], 
                "desc": "죄송합니다. 현재 프론트 데스크의 연결이 고르지 않아 방을 배정할 수 없습니다. 잠시 후 다시 종을 울려주시겠습니까?", 
                "stills": [
                    "https://images.unsplash.com/photo-1485846234645-a62644f84728?q=80&w=800&auto=format&fit=crop",
                    "https://images.unsplash.com/photo-1485846234645-a62644f84728?q=80&w=800&auto=format&fit=crop",
                    "https://images.unsplash.com/photo-1485846234645-a62644f84728?q=80&w=800&auto=format&fit=crop"
                ]
            }
            
        session.modified = True
        return render_template('result.html', rec_data=rec_data)
        
    return render_template('result.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_text = data.get('message')
    chat_history = session.get('chat_history', [{"role": "system", "content": CONCIERGE_PROMPT}])
    chat_history.append({"role": "user", "content": user_text})
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=chat_history,
            temperature=0.7
        )
        bot_reply = response.choices[0].message.content
        clean_reply = re.sub(r'\[TITLE\]|\[OTT\]|\[DESC\]', '', bot_reply).strip()
        chat_history.append({"role": "assistant", "content": bot_reply})
        session['chat_history'] = chat_history
        session.modified = True
        return jsonify({"reply": clean_reply})
    except Exception:
        # 채팅 에러 메시지 역시 세계관 유지
        return jsonify({"reply": "통신에 잡음이 섞여 손님의 목소리가 닿지 않았습니다. 다시 한 번 말씀해 주시겠습니까?"})

@app.route('/trends')
def trends():
    # 3. 방명록 샘플  데이터의 어조도 지배인의 기록처럼 우아하게 다듬음
    mock_trends_data = [
        {"emotion": "지치고 위로가 필요함", "title": "나의 아저씨", "otts": ["Netflix", "Tving"], "desc": "하루의 무거운 짐을 내려놓고자 하셨던 손님입니다. 이 방에서 온전한 안식을 찾고 떠나셨습니다."},
        {"emotion": "잔잔하고 평온함", "title": "리틀 포레스트", "otts": ["Netflix", "Watcha"], "desc": "자극 없는 힐링을 원하셨기에, 조용한 시골의 사계절이 담긴 이 방을 내어드렸습니다."}
    ]
    return render_template('trends.html', trends=mock_trends_data)

if __name__ == '__main__':
    app.run(debug=True)