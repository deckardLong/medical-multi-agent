import { ArrowLeft } from "lucide-react";
import { Link } from "react-router-dom";
import { AureliaMark } from "../../components/AureliaMark";
import s from "./legal.module.css";

/*
 * Ba trang công khai (không cần đăng nhập) mà Meta/Google yêu cầu khi bật đăng nhập bằng Facebook/Google:
 * /privacy, /terms, /data-deletion. Nội dung mô tả ĐÚNG cách hệ thống xử lý dữ liệu hiện tại — sửa code xử lý dữ liệu
 * (thêm dịch vụ bên ngoài, đổi nơi lưu) thì phải sửa cả trang này.
 * Email liên hệ lấy từ VITE_CONTACT_EMAIL (không ghi cứng email cá nhân vào mã nguồn).
 */
export const CONTACT_EMAIL = (import.meta.env.VITE_CONTACT_EMAIL as string | undefined)?.trim() || "";
const UPDATED = "28/11/2026";

function Contact() {
  return CONTACT_EMAIL
    ? <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>
    : <strong>(chưa cấu hình email liên hệ — đặt biến VITE_CONTACT_EMAIL)</strong>;
}

function Shell({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className={s.page}>
      <header className={s.head}>
        <Link to="/" className={s.brand}><span className={s.mark}><AureliaMark size={22} /></span>AURELIA</Link>
        <nav className={s.nav}>
          <Link to="/privacy">Quyền riêng tư</Link>
          <Link to="/terms">Điều khoản</Link>
          <Link to="/data-deletion">Xoá dữ liệu</Link>
        </nav>
      </header>
      <article className={s.doc}>
        <Link to="/login" className={s.back}><ArrowLeft size={16} />Về trang đăng nhập</Link>
        <h1>{title}</h1>
        <p className={s.meta}>Cập nhật lần cuối: {UPDATED}</p>
        {children}
      </article>
    </div>
  );
}

export function PrivacyPage() {
  return (
    <Shell title="Chính sách quyền riêng tư">
      <p>
        AURELIA là trợ lý sức khoẻ gia đình do một cá nhân phát triển và vận hành (dự án cá nhân, phi thương mại).
        Trang này giải thích AURELIA thu thập dữ liệu gì, dùng vào việc gì, lưu ở đâu và bạn xoá dữ liệu như thế nào.
        Dữ liệu sức khoẻ là dữ liệu cá nhân nhạy cảm; AURELIA chỉ xử lý khi bạn đồng ý lúc đăng ký.
      </p>

      <h2>1. Dữ liệu được thu thập</h2>
      <ul>
        <li><b>Tài khoản:</b> email, họ, tên; tuỳ chọn ngày sinh, giới tính, số điện thoại. Mật khẩu chỉ được lưu dưới dạng
          băm (bcrypt), không ai đọc được mật khẩu gốc.</li>
        <li><b>Đăng nhập bằng Google hoặc Facebook:</b> chỉ lấy <b>tên, email và mã định danh tài khoản</b> do Google/Facebook
          cung cấp. AURELIA không đọc danh sách bạn bè, ảnh, bài viết và không đăng bất cứ điều gì lên tài khoản của bạn.</li>
        <li><b>Thành viên gia đình</b> bạn thêm vào (tên, quan hệ, ngày sinh) và <b>ảnh đại diện</b>. Ảnh đại diện được thu
          nhỏ và xoá toàn bộ thông tin EXIF (gồm vị trí GPS) trước khi lưu.</li>
        <li><b>Hồ sơ sức khoẻ</b> bạn nhập hoặc xác nhận: dị ứng, bệnh nền, thuốc đang dùng, kết quả xét nghiệm.</li>
        <li><b>Nội dung trò chuyện</b> với AURELIA và <b>ảnh đơn thuốc</b> bạn tải lên.</li>
        <li><b>Lịch khám, lịch nhắc uống thuốc</b> bạn tạo hoặc xác nhận.</li>
      </ul>

      <h2>2. Mục đích sử dụng</h2>
      <ul>
        <li>Trả lời câu hỏi sức khoẻ có tham khảo hồ sơ của đúng thành viên đang được hỏi (ví dụ cảnh báo dị ứng).</li>
        <li>Đọc ảnh đơn thuốc và tạo đề xuất hồ sơ — đề xuất chỉ có hiệu lực khi bạn bấm xác nhận.</li>
        <li>Gửi email nhắc lịch khám, lịch uống thuốc mà bạn đã xác nhận.</li>
      </ul>
      <p>AURELIA <b>không bán dữ liệu, không hiển thị quảng cáo</b> và không dùng dữ liệu của bạn để huấn luyện mô hình AI.</p>

      <h2>3. Nơi lưu trữ và các bên liên quan</h2>
      <ul>
        <li>Cơ sở dữ liệu, ảnh tải lên và các mô hình AI (trả lời câu hỏi, đọc ảnh) chạy trên <b>máy chủ do người vận hành
          tự quản lý</b>. Câu hỏi và ảnh đơn thuốc <b>không</b> được gửi cho các nhà cung cấp AI bên ngoài.</li>
        <li><b>Vercel</b> phục vụ giao diện web; <b>Cloudflare</b> chuyển tiếp kết nối (mã hoá HTTPS) giữa trình duyệt và máy chủ.</li>
        <li><b>Tavily</b> (tìm kiếm web): khi kho tài liệu y khoa không có câu trả lời, nội dung truy vấn tìm kiếm được gửi tới
          Tavily để tìm trên các trang y tế uy tín. Truy vấn không kèm tên, email hay hồ sơ của bạn.</li>
        <li><b>Gmail (SMTP)</b>: email nhắc lịch được gửi qua máy chủ email của Google, gồm tiêu đề và thời gian lịch hẹn.</li>
        <li><b>Google / Facebook</b>: chỉ khi bạn chọn đăng nhập bằng tài khoản của họ, để xác minh danh tính.</li>
      </ul>

      <h2>4. Ai xem được dữ liệu của bạn</h2>
      <p>
        Hồ sơ của mỗi thành viên chỉ chủ gia đình (với thành viên chưa có tài khoản, như con nhỏ) hoặc chính thành viên đó
        (khi đã liên kết tài khoản) xem được. Người vận hành hệ thống có quyền truy cập kỹ thuật vào cơ sở dữ liệu và chỉ
        dùng để vận hành, sửa lỗi hoặc thực hiện yêu cầu xoá dữ liệu của bạn.
      </p>

      <h2>5. Lưu trữ và xoá</h2>
      <p>
        Dữ liệu được giữ cho tới khi bạn yêu cầu xoá. Cách xoá xem tại trang <Link to="/data-deletion">Hướng dẫn xoá dữ
        liệu</Link>.
      </p>

      <h2>6. Lưu ý</h2>
      <p>
        AURELIA không phải là thiết bị y tế và không thay thế bác sĩ. Đây là dự án cá nhân đang thử nghiệm; không nên nhập
        thông tin sức khoẻ thật nếu bạn không đồng ý với các điều trên.
      </p>

      <h2>7. Liên hệ</h2>
      <p>Mọi câu hỏi về quyền riêng tư: <Contact />.</p>
    </Shell>
  );
}

export function TermsPage() {
  return (
    <Shell title="Điều khoản sử dụng">
      <h2>1. Dịch vụ</h2>
      <p>
        AURELIA cung cấp công cụ lưu hồ sơ sức khoẻ gia đình, nhắc lịch và trả lời câu hỏi sức khoẻ dựa trên tài liệu tham
        khảo. AURELIA là dự án cá nhân, cung cấp miễn phí và &quot;như hiện có&quot;, có thể gián đoạn hoặc ngừng hoạt động bất cứ lúc nào.
      </p>

      <h2>2. Không thay thế tư vấn y tế</h2>
      <p>
        Thông tin AURELIA đưa ra chỉ để tham khảo, có thể sai hoặc không đầy đủ, và <b>không phải chẩn đoán hay chỉ định
        điều trị</b>. Luôn hỏi bác sĩ, dược sĩ trước khi dùng thuốc. Khi có dấu hiệu nguy hiểm (khó thở, đau ngực, co giật,
        chảy máu không cầm…), gọi <b>115</b> hoặc đến cơ sở cấp cứu gần nhất ngay. Kết quả đọc ảnh đơn thuốc phải được bạn
        kiểm tra lại với đơn gốc trước khi xác nhận.
      </p>

      <h2>3. Tài khoản</h2>
      <ul>
        <li>Bạn cần đủ 18 tuổi để tạo tài khoản; thông tin của trẻ em chỉ được cha mẹ hoặc người giám hộ thêm vào gia đình.</li>
        <li>Bạn chịu trách nhiệm giữ bí mật mật khẩu và về tính chính xác của thông tin mình nhập.</li>
        <li>Chỉ thêm thông tin của người khác khi bạn có quyền hoặc được họ đồng ý.</li>
      </ul>

      <h2>4. Hành vi không được phép</h2>
      <p>
        Không dùng AURELIA để truy cập dữ liệu của người khác, tấn công hay làm quá tải hệ thống, hoặc tải lên nội dung
        vi phạm pháp luật.
      </p>

      <h2>5. Giới hạn trách nhiệm</h2>
      <p>
        Trong phạm vi pháp luật cho phép, người vận hành không chịu trách nhiệm về thiệt hại phát sinh từ việc dựa vào
        thông tin do AURELIA cung cấp thay cho ý kiến của nhân viên y tế.
      </p>

      <h2>6. Quyền riêng tư</h2>
      <p>Cách AURELIA xử lý dữ liệu được mô tả tại <Link to="/privacy">Chính sách quyền riêng tư</Link>.</p>

      <h2>7. Liên hệ</h2>
      <p><Contact /></p>
    </Shell>
  );
}

export function DataDeletionPage() {
  return (
    <Shell title="Hướng dẫn xoá dữ liệu">
      <p>Bạn có thể yêu cầu xoá toàn bộ dữ liệu của mình bất cứ lúc nào, kể cả khi bạn đăng nhập bằng Facebook hoặc Google.</p>

      <h2>Yêu cầu xoá tài khoản và dữ liệu</h2>
      <ol>
        <li>Gửi email tới <Contact /> với tiêu đề <b>&quot;Yêu cầu xoá dữ liệu AURELIA&quot;</b>.</li>
        <li>Gửi <b>từ chính địa chỉ email của tài khoản</b> (email bạn dùng để đăng ký, hoặc email của tài khoản
          Google/Facebook bạn dùng để đăng nhập), để xác nhận bạn là chủ tài khoản.</li>
        <li>Trong vòng <b>30 ngày</b>, toàn bộ dữ liệu sau sẽ bị xoá vĩnh viễn và bạn nhận email xác nhận:
          <ul>
            <li>tài khoản và liên kết Google/Facebook;</li>
            <li>gia đình, các thành viên do bạn quản lý và ảnh đại diện;</li>
            <li>hồ sơ sức khoẻ, lịch, lịch sử trò chuyện, ảnh đơn thuốc đã tải lên.</li>
          </ul>
        </li>
      </ol>
      <p>
        Nếu bạn là thành viên được liên kết vào gia đình của người khác, dữ liệu trong hồ sơ của chính bạn sẽ bị xoá; gia
        đình của người kia vẫn được giữ nguyên.
      </p>

      <h2>Gỡ quyền truy cập Facebook</h2>
      <p>
        Bạn cũng có thể gỡ AURELIA khỏi tài khoản Facebook: <b>Cài đặt &amp; quyền riêng tư → Cài đặt → Ứng dụng và trang web</b>,
        chọn AURELIA rồi bấm <b>Gỡ</b>. Việc này chỉ ngừng chia sẻ thông tin Facebook với AURELIA; để xoá dữ liệu đã lưu, hãy
        gửi yêu cầu như trên.
      </p>

      <h2>Gỡ quyền truy cập Google</h2>
      <p>
        Vào <a href="https://myaccount.google.com/connections" target="_blank" rel="noreferrer">myaccount.google.com/connections</a>,
        chọn AURELIA và xoá kết nối.
      </p>
    </Shell>
  );
}
