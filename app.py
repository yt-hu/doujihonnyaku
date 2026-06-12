import streamlit as st
import google.generativeai as genai
from openai import OpenAI
import io
import datetime
# マイク録音用ライブラリ (事前に pip install audio-recorder-streamlit が必要です)
from audio_recorder_streamlit import audio_recorder

# ==========================================
# 初期設定とセッション状態の初期化
# ==========================================
st.set_page_config(page_title="Nuance Translator", layout="wide")

if "history" not in st.session_state:
    st.session_state.history = []
if "current_transcription" not in st.session_state:
    st.session_state.current_transcription = ""
if "current_translation" not in st.session_state:
    st.session_state.current_translation = ""

# ==========================================
# サイドバー: APIキーの設定
# ==========================================
with st.sidebar:
    st.header("API Key Settings")
    openai_api_key = st.text_input("OpenAI API Key (for Whisper)", type="password")
    gemini_api_key = st.text_input("Gemini API Key", type="password")
    
    st.markdown("---")
    st.markdown("### アプリの機能")
    st.markdown("- 🎙️ 英語音声の録音と文字起こし (Whisper)\n- 🧠 ニュアンス翻訳 (Gemini)\n- 📝 翻訳履歴と評価の保存")

# ==========================================
# メイン画面: 翻訳アプリのUI
# ==========================================
st.title("🗣️ Nuance Translator for Discussions")
st.write("留学生とのディスカッション（デザイン理論・聖書研究など）の文脈を汲み取り、自然な日本語に翻訳します。")

# 1. マイクボタンで英語音声を録音 (機能1)
st.subheader("1. 音声入力")
audio_bytes = audio_recorder(text="マイクアイコンをクリックして録音開始/停止", icon_size="2x")

if audio_bytes and openai_api_key and gemini_api_key:
    # 音声データが新しく録音された場合の処理
    st.success("録音が完了しました。文字起こしと翻訳を開始します...")
    
    try:
        # Whisper APIで文字起こし (機能1)
        client = OpenAI(api_key=openai_api_key)
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.wav"
        
        with st.spinner("Whisperで文字起こし中..."):
            transcription = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
            st.session_state.current_transcription = transcription.text

        # Gemini APIでニュアンス翻訳 (機能2)
        genai.configure(api_key=gemini_api_key)
        # Gemini 1.5 FlashまたはProを使用
        model = genai.GenerativeModel('gemini-1.5-flash') 
        
        # コンテキストを自動判断させるシステムプロンプト
        prompt = f"""
        あなたは、海外の留学生との高度なディスカッションをサポートするプロの同時通訳者です。
        以下の英語テキストの文脈を自動的に判断し、最も適切なトーンと専門用語で日本語に翻訳してください。

        【想定される主なトピックと翻訳方針】
        - デザイン理論: 客観的、論理的、美学的な語彙を使用。学術的で洗練されたトーン。
        - 聖書研究・哲学: 隠喩、歴史的背景、神学的なニュアンスを深く理解し、敬意を持った自然で思慮深いトーン。
        - 日常会話・その他: スムーズでフレンドリーなトーン。

        【英語テキスト】
        {st.session_state.current_transcription}
        
        【出力ルール】
        翻訳された日本語のテキストのみを出力してください。解説は不要です。
        """
        
        with st.spinner("Geminiでニュアンスを考慮して翻訳中..."):
            response = model.generate_content(prompt)
            st.session_state.current_translation = response.text
            
    except Exception as e:
        st.error(f"エラーが発生しました: {e}")

# 2. 翻訳結果のリアルタイム表示 (機能3)
if st.session_state.current_transcription:
    st.subheader("2. 翻訳結果")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**原文 (English)**")
        st.info(st.session_state.current_transcription)
    with col2:
        st.markdown("**翻訳 (Japanese)**")
        st.success(st.session_state.current_translation)

    # 3. 評価・フィードバック機能 (機能5)
    st.subheader("3. 翻訳の評価・フィードバック")
    with st.form("evaluation_form", clear_on_submit=True):
        col_eval1, col_eval2 = st.columns(2)
        with col_eval1:
            naturalness = st.slider("翻訳の自然さ", 1, 5, 3)
            nuance = st.slider("文脈・ニュアンスの正確さ", 1, 5, 3)
        with col_eval2:
            feedback_note = st.text_area("メモ・改善点 (例: この単語はもっと神学的な意味合いが強い、など)")
        
        submit_eval = st.form_submit_button("評価を保存して履歴に追加")
        
        if submit_eval:
            # 履歴に保存 (機能4)
            record = {
                "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "original": st.session_state.current_transcription,
                "translation": st.session_state.current_translation,
                "naturalness": naturalness,
                "nuance": nuance,
                "note": feedback_note
            }
            st.session_state.history.append(record)
            st.toast("履歴に保存されました！")
            
            # 現在の表示をクリアして次の録音に備える
            st.session_state.current_transcription = ""
            st.session_state.current_translation = ""
            st.rerun()

# 4. 過去の翻訳履歴の一覧表示 (機能4)
st.markdown("---")
st.subheader("📚 過去の翻訳履歴")
if st.session_state.history:
    for i, item in enumerate(reversed(st.session_state.history)):
        with st.expander(f"[{item['timestamp']}] 評価: 自然さ {item['naturalness']}/5, ニュアンス {item['nuance']}/5"):
            st.markdown(f"**原文:** {item['original']}")
            st.markdown(f"**翻訳:** {item['translation']}")
            if item['note']:
                st.markdown(f"**メモ:** {item['note']}")
else:
    st.write("履歴はまだありません。")
