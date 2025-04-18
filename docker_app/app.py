from flask import Flask, render_template, request, send_file, redirect, url_for
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from io import BytesIO
import requests
import time
from constants import BLACK_COVER_IMG, BLACK_GRP_IMAGE
import threading
import os

progress_thread = None
pdfmetrics.registerFont(TTFont('Symbola', 'Symbola.ttf'))

app = Flask(__name__)

class ProgressThread(threading.Thread):
    def __init__(self, email, password):
        self.progress = 0
        self.email = email
        self.password = password
        super().__init__()

    def run(self):
        auth_url = "https://centralised.sarc-iitb.org/api/authenticate/token/"
        auth_payload = {"username": self.email,"password": self.password}
        response = requests.post(auth_url, json=auth_payload,headers={"Content-Type": "application/json"})
        access_token = response.json()['access']
        auth_header = {"Authorization": f"Bearer {access_token}"}
        userId = requests.get("https://centralised.sarc-iitb.org/api/authenticate/current_user/",headers=auth_header).json()['id']
        messagesForYou = requests.get(f"https://centralised.sarc-iitb.org/api/posts/others/{userId}",headers=auth_header).json()
        messagesByYou = requests.get(f"https://centralised.sarc-iitb.org/api/posts/my/{userId}",headers=auth_header).json()
        userPhotos = requests.get(f"https://centralised.sarc-iitb.org/api/authenticate/profile/{userId}/gallery/",headers=auth_header).json()
        self.maxProg = len(messagesForYou) + len(messagesByYou)
        self.progress = 0
        self.generate_pdf(messagesForYou, messagesByYou, userPhotos, "yearbook.pdf", auth_header)

    def add_message_block(self, c, message, y_position, auth_header):
        width, height = letter

        c.setStrokeColor(colors.purple)
        c.setLineWidth(1)
        c.line(50, y_position, width - 50, y_position)

        try: 
            profile_image_url = message['written_by_profile']['profile_image']
            if profile_image_url:
                response = requests.get("https://centralised.sarc-iitb.org" + profile_image_url,headers=auth_header)
                profile_img = ImageReader(BytesIO(response.content))
                c.drawImage(profile_img, 60, y_position - 60, 50, 50)
        except:
            time.sleep(0)


        profile_image_url = message['written_for_profile']['profile_image']
        if profile_image_url:
            response = requests.get("https://centralised.sarc-iitb.org" + profile_image_url,headers=auth_header)
            profile_img = ImageReader(BytesIO(response.content))
            c.drawImage(profile_img, width - 260, y_position - 60, 50, 50)


        written_by = "From: " + message['written_by']
        written_for = "To: " + message['written_for']
        c.setFont("Helvetica-Bold", 12)
        c.setFillColor(colors.purple)
        c.drawString(120, y_position - 20, f"{written_by}")
        c.drawString(width - 200, y_position - 20, f"{written_for}")

        c.setFont("Helvetica", 10)
        c.setFillColor(colors.black)

        if message['written_by_dept'] != "None" and message['written_by_year'] != "None":
            if '&' in message["written_by_dept"]:
                p = message["written_by_dept"].split('&')
                c.drawString(120, y_position - 40, f"{p[0]}")
                c.drawString(120, y_position - 55, f"{'&' + p[1]}")
                c.drawString(120, y_position - 70, f"{message['written_by_year']}")
            elif 'and' in message["written_by_dept"]:
                p = message["written_by_dept"].split('and')
                c.drawString(120, y_position - 40, f"{p[0]}")
                c.drawString(120, y_position - 55, f"{'and' + p[1]}")
                c.drawString(120, y_position - 70, f"{message['written_by_year']}")
            else:
                c.drawString(120, y_position - 40, f"{message['written_by_dept']}")
                c.drawString(120, y_position - 55, f"{message['written_by_year']}")
        
        if '&' in message["written_for_dept"]:
            p = message["written_for_dept"].split('&')
            c.drawString(width - 200, y_position - 40, f"{p[0]}")
            c.drawString(width - 200, y_position - 55, f"{'&' + p[1]}")
            c.drawString(width - 200, y_position - 70, f"{message['written_for_year']}")
        elif ' and ' in message["written_for_dept"]:
            p = message["written_for_dept"].split('and')
            c.drawString(width - 200, y_position - 40, f"{p[0]}")
            c.drawString(width - 200, y_position - 55, f"{'and' + p[1]}")
            c.drawString(width - 200, y_position - 70, f"{message['written_for_year']}")
        else:
            c.drawString(width - 200, y_position - 40, f"{message['written_for_dept']}")
            c.drawString(width - 200, y_position - 55, f"{message['written_for_year']}")


        c.setFont("Symbola",12)
        content = message['content']
        text_object = c.beginText(60, y_position - 85)
        text_object.setFont("Symbola", 12)
        max_width = width - 120
        content_height = 0 
        current_y_position = y_position - 85

        for line in content.splitlines():
            words = line.split()
            current_line = ""

            for word in words:
                test_line = current_line + word + " "
                if c.stringWidth(test_line) <= max_width:
                    current_line = test_line
                else:
                    text_object.textLine(current_line.strip())
                    content_height += 12
                    current_y_position -= 12

                    if current_y_position < 50:
                        c.drawText(text_object)
                        c.showPage()
                        text_object = c.beginText(60, height - 50)
                        text_object.setFont("Symbola", 12)
                        current_y_position = height - 50

                    current_line = word + " "

            if current_line:
                text_object.textLine(current_line.strip())
                content_height += 12
                current_y_position -= 12

                if current_y_position < 50:
                    c.drawText(text_object)
                    c.showPage()
                    text_object = c.beginText(60, height - 50)
                    text_object.setFont("Symbola", 12)
                    current_y_position = height - 50

        c.drawText(text_object)

        return current_y_position - 50

    def generate_pdf(self, messagesForYou, messagesByYou, userPhotos, output_file, auth_header):
        c = canvas.Canvas(output_file, pagesize=letter)
        width, height = letter

        c.setFont("Helvetica-Bold", 20)
        c.setFillColor(colors.purple)
        c.drawString(125, 750, "Yearbook - Your College Memories")
        c.setFont("Helvetica", 12)
        c.drawString(100, 730, "Let's take a stroll through time and remember the good times we had together!")

        c.setStrokeColor(colors.purple)
        c.setLineWidth(1)
        c.line(50, 720, width - 50, 720)

        imagesInserted = False
        coverPhotoInserted = False
        groupPhotosInserted = False

        try:
            coverImageURL = "https://centralised.sarc-iitb.org" + userPhotos["cover"]
            response = requests.get(coverImageURL, headers=auth_header)
            if response.content != BLACK_COVER_IMG:
                coverImage = ImageReader(BytesIO(response.content))
                c.drawImage(coverImage, 50, 545, width - 100, (width - 100)*0.3) # 10:3 aspect ratio
                coverPhotoInserted = True
            groupImageRawData = [requests.get("https://centralised.sarc-iitb.org" + userPhotos[t], headers=auth_header).content for t in userPhotos if t.startswith("img")]
            groupImages = [ImageReader(BytesIO(t)) for t in groupImageRawData if t != BLACK_GRP_IMAGE]
            if len(groupImages) > 0:
                c.setFillColor(colors.purple)
                c.setFont("Helvetica", 12)
                c.drawString(175, 510, "Refresh your memories with these group photos!")
                groupPhotosInserted = True
            for i in range(len(groupImages)):
                c.drawImage(groupImages[i], 50 + (i % 2) * 265, 310 - (i // 2) * 200, (width - 110)/2, (width - 110)/2 * (2/3)) # 3:2 aspect ratio
            imagesInserted = coverPhotoInserted or groupPhotosInserted
        except:
            time.sleep(0)

        if imagesInserted:
            c.showPage()
            c.setFont("Helvetica-Bold", 20)
            c.setFillColor(colors.purple)
            c.drawString(175, 750, "What people wrote for you")
            y_position = 720
        else:
            c.setFont("Helvetica-Bold", 20)
            c.setFillColor(colors.purple)
            c.drawString(175, 690, "What people wrote for you")
            y_position = 670

        for message in messagesForYou:
            if y_position < 150: 
                c.showPage()
                y_position = 750
            y_position = self.add_message_block(c, message, y_position, auth_header)
            self.progress += 100/self.maxProg
        
        
        c.showPage()
        c.setFont("Helvetica-Bold", 20)
        c.setFillColor(colors.purple)
        c.drawString(175, 750, "What you wrote for others")

        y_position = 720
        
        for message in messagesByYou:
            if y_position < 150: 
                c.showPage()
                y_position = 750
            y_position = self.add_message_block(c, message, y_position, auth_header)
            self.progress += 100/self.maxProg
        c.save()

@app.route('/')
def home():
    return render_template("index.html")

@app.route('/process', methods=['POST', 'GET'])
def process():
    if request.method == 'POST':
        global progress_thread
        email = request.form['email']
        password = request.form['password']
        progress_thread = ProgressThread(email=email, password=password)
        progress_thread.start()
        return render_template("progress.html")
    else:
        return redirect(url_for('home'))

@app.route('/download', methods=['GET'])
def download():
    if os.path.exists("yearbook.pdf"):
        return send_file(
            'yearbook.pdf',
            as_attachment=True,
            download_name="yearbook.pdf",
            mimetype='application/pdf'
        ), 200
    else:
        return "Yearbook is not generated yet", 404

@app.route('/progress', methods=['GET'])
def progress():
    global progress_thread
    if progress_thread is not None:
        return str(int(progress_thread.progress)), 200
    else:
        return "Yearbook generation not started", 404

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=8000)