EXTRACT = """Đây là ảnh đơn thuốc. Trích xuất CHÍNH XÁC những gì nhìn thấy, không đoán, không sửa chính tả tên thuốc.
Trường nào không đọc được thì để null. "name" CHỈ là tên thuốc — hàm lượng/liều ghi vào "dose", số lần dùng
(vd 8hrly, 2 lần/ngày, nocte) ghi vào "frequency", số ngày ghi vào "duration". Chỉ trả về JSON đúng khuôn:
{"medications":[{"name":"","dose":"","frequency":"","duration":""}],"prescriber":"","issued_date":"YYYY-MM-DD","facility":""}"""

TRANSCRIBE = """Chép lại NGUYÊN VĂN mọi dòng chữ trong ảnh, mỗi dòng một hàng, giữ đúng thứ tự từ trên xuống.
Không giải thích, không sửa lỗi, chữ nào không đọc được thì ghi [?]."""

STRUCTURE_FROM_TEXT = """Dưới đây là chữ được chép từ một đơn thuốc (có thể có lỗi nhận dạng).
Chỉ dùng thông tin có trong văn bản, không suy đoán thêm. Trường nào không có thì để null.
Chép tên thuốc ĐÚNG NHƯ trong văn bản kể cả khi có vẻ sai chính tả do lỗi nhận dạng — không sửa, không bỏ
thuốc chỉ vì tên khó đọc. "facility" là tên cơ sở y tế in ở đầu đơn. "name" CHỈ là tên
thuốc — hàm lượng/liều ghi vào "dose", số lần dùng (vd 8hrly, 2 lần/ngày, nocte) ghi vào "frequency", số ngày
ghi vào "duration". Trả về JSON đúng khuôn:
{{"medications":[{{"name":"","dose":"","frequency":"","duration":""}}],"prescriber":"","issued_date":"YYYY-MM-DD","facility":""}}

VĂN BẢN:
{text}"""