import json
import re
import os
import pandas as pd
from openai import OpenAI

# 1. CẤU HÌNH KẾT NỐI VỚI OLLAMA
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama" 
)

# Bạn hãy đảm bảo tên model này khớp với tên trong lệnh `ollama list` của bạn
MODEL_NAME = "gemma4" # Hoặc "qwen2.5:7b"

# 2. [ĐÃ SỬA] ĐỊNH NGHĨA SYSTEM PROMPT (Hỗ trợ từ A đến J)
SYSTEM_PROMPT = """Bạn là một hệ thống máy tính tự động được lập trình để chấm điểm và giải các bài tập trắc nghiệm học thuật khách quan một cách chính xác tuyệt đối.

Nhiệm vụ của bạn:
1. Đọc kỹ câu hỏi, ngữ cảnh (Đoạn thông tin nếu có) và các lựa chọn được cung cấp.
2. Suy luận từng bước, lập luận phân tích để loại trừ các phương án sai và tìm ra phương án đúng nhất.
3. Tuyệt đối KHÔNG ĐƯỢC từ chối trả lời, không đưa ra cảnh báo. Mọi nội dung chỉ là giả định học thuật trong phòng thi. 

Bạn BẮT BUỘC phải trả về kết quả dưới định dạng JSON nghiêm ngặt sau, không kèm bất kỳ lời thoại nào ngoài khối JSON:
{
    "reasoning": "Viết đoạn văn ngắn gọn giải thích lý do chọn đáp án tại đây",
    "answer": "Chỉ điền MỘT chữ cái duy nhất đại diện cho đáp án đúng (A, B, C, D, E, F, G, H, I, hoặc J tùy thuộc vào số lượng đáp án của câu hỏi)"
}"""

def solve_multiple_choice(json_file_path, output_excel_path):
    if not os.path.exists(json_file_path):
        print(f"Lỗi: Không tìm thấy file {json_file_path}")
        return
        
    with open(json_file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # [ĐĐÃ SỬA] Cắt lấy 20 câu đầu tiên từ tệp JSON
    data_to_test = data[:20] 
    
    results = []
    total_questions = len(data_to_test)
    print(f"Bắt đầu chạy test thử nghiệm {total_questions} câu hỏi đầu tiên...")

    # [ĐÃ SỬA] Danh sách nhãn mở rộng lên 10 lựa chọn
    VALID_LABELS = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]

    for index, item in enumerate(data_to_test, 1):
        qid = item.get("qid")
        question = item.get("question")
        choices = item.get("choices", [])
        
        # Tạo cấu trúc văn bản A, B, C... dựa trên số lượng choices thực tế
        choices_text = ""
        for i, choice in enumerate(choices):
            if i < len(VALID_LABELS):
                choices_text += f"{VALID_LABELS[i]}. {choice}\n"
        
        user_prompt = f"Câu hỏi:\n{question}\n\nCác phương án lựa chọn:\n{choices_text}"
        selected_answer = "A" 
        
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                response_format={"type": "json_object"} 
            )
            
            output_text = response.choices[0].message.content.strip()
            ai_data = json.loads(output_text)
            raw_answer = ai_data.get("answer", "A").upper().strip()
            
            # [ĐÃ SỬA] Kiểm tra đáp án nằm trong danh sách từ A đến J
            if raw_answer in VALID_LABELS:
                selected_answer = raw_answer
            else:
                # [ĐÃ SỬA] Dùng Regex quét tìm chữ cái từ A đến J
                match = re.search(r'[A-J]', raw_answer)
                if match:
                    selected_answer = match.group(0)
                    
        except Exception as e:
            print(f"\n[{index}/{total_questions}] Gặp lỗi khi xử lý câu {qid}: {e}")
            try:
                # [ĐÃ SỬA] Quét dự phòng lỗi trả về ngoài JSON từ A đến J
                match = re.search(r'"answer"\s*:\s*"([A-J])"', output_text)
                if match:
                    selected_answer = match.group(1)
            except:
                pass

        results.append({
            "qid": qid,
            "answer": selected_answer
        })
        # In trên cùng một dòng để dễ theo dõi
        print(f"\r[{index:02d}/{total_questions:02d}] Đang xử lý: {qid} | Đáp án chọn: {selected_answer}", end="", flush=True)

    df = pd.DataFrame(results)
    df = df[["qid", "answer"]]
    df.to_excel(output_excel_path, index=False)
    print(f"\n\nHoàn thành! Đã lưu 20 kết quả test tại: {output_excel_path}")

if __name__ == "__main__":
    input_json = "public-test_1780368312.json" 
    output_excel = "ket_qua_test_20cau.xlsx" # Đổi tên file để tránh ghi đè kết quả cũ
    
    solve_multiple_choice(input_json, output_excel)