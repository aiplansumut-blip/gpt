import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import os

# --- Konfigurasi Halaman ---
st.set_page_config(
    page_title="AI Plan Sumut Assistant",
    page_icon="🤖",
    layout="centered"  # Tampilan lebih fokus seperti chat app
)

# --- CSS Custom (Agar tampilan lebih bersih/profesional) ---
st.markdown("""
<style>
    .stChatFloatingInputContainer {bottom: 20px;}
    .reportview-container {margin-top: -2em;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.title("🤖 AI Assistant - Dokumen Internal")
st.markdown("Tanyakan apa saja terkait dokumen perencanaan/data yang tersimpan di sistem.")

# --- KONFIGURASI KEAMANAN (PENTING) ---
# Mengambil API Key dari Streamlit Secrets (bukan hardcode)
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except FileNotFoundError:
    st.error("API Key belum disetting di Secrets! Harap hubungi administrator.")
    st.stop()

# --- Fungsi Caching (Agar tidak baca PDF berulang-ulang) ---
# Fungsi ini hanya jalan 1x saat server restart atau code berubah
@st.cache_resource
def load_all_documents():
    folder_path = "data" # Pastikan folder ini ada di GitHub
    combined_text = ""
    file_count = 0
    
    # Cek apakah folder ada
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        return "", 0

    # Loop semua file di folder data
    for filename in os.listdir(folder_path):
        if filename.endswith(".pdf"):
            file_path = os.path.join(folder_path, filename)
            try:
                pdf_reader = PdfReader(file_path)
                for page in pdf_reader.pages:
                    text = page.extract_text()
                    if text:
                        combined_text += text + "\n"
                file_count += 1
            except Exception as e:
                print(f"Gagal membaca {filename}: {e}")
                
    return combined_text, file_count

# --- Load Data Saat Aplikasi Mulai ---
with st.spinner("Menyiapkan basis pengetahuan AI..."):
    knowledge_base, total_files = load_all_documents()

if total_files == 0:
    st.warning("⚠️ Belum ada dokumen di folder 'data/'. Silakan upload ke repository GitHub.")
else:
    # Tampilkan info kecil di sidebar (opsional)
    with st.sidebar:
        st.info(f"✅ Sistem Terhubung\n📚 {total_files} Dokumen dimuat.")
        st.markdown("---")
        st.write("Sistem ini menggunakan Gemini 1.5 Flash untuk menjawab pertanyaan berdasarkan dokumen internal.")

# --- Logic Chat ---

# Inisialisasi history chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Halo! Saya siap membantu menjawab pertanyaan dari dokumen yang tersedia."}
    ]

# Tampilkan chat yang sudah lalu
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input User
if prompt := st.chat_input("Ketik pertanyaan Anda di sini..."):
    # 1. Tampilkan pertanyaan user
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Proses Jawaban
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        try:
            # Prompt Engineering untuk membatasi jawaban hanya dari data
            full_prompt = f"""
            Anda adalah asisten AI profesional untuk organisasi.
            Tugas Anda adalah menjawab pertanyaan pengguna BERDASARKAN konteks dokumen di bawah ini.
            
            KONTEKS DOKUMEN:
            {knowledge_base}
            
            ATURAN:
            1. Jawablah dengan sopan dan profesional (Bahasa Indonesia).
            2. Gunakan HANYA informasi dari "KONTEKS DOKUMEN" di atas.
            3. Jika jawaban tidak ditemukan di dokumen, katakan: "Mohon maaf, informasi tersebut tidak tersedia dalam dokumen internal kami." Jangan mengarang jawaban.
            
            PERTANYAAN PENGGUNA:
            {prompt}
            """
            
            # Panggil Gemini
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(full_prompt)
            answer = response.text
            
            message_placeholder.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})
            
        except Exception as e:
            message_placeholder.error("Maaf, terjadi gangguan koneksi ke AI.")