import json
import os
import shutil
import uuid

from fastapi import BackgroundTasks, FastAPI, File, Request, UploadFile
from fastapi.templating import Jinja2Templates

import ocr

app = FastAPI()
templates = Jinja2Templates(directory="templates")


@app.get("/")
def home(request: Request):
    # Hàm này trả về một template html cho trang web
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/api/v1/extract_text")
# extract single image
async def extract_text(image: UploadFile = File(...)):
    temp_file = _save_file_to_disk(image, path="./temp", save_as="temp")
    # Lưu file dưới local và dùng file đó cho ocr.
    text = await ocr.read_image(temp_file)
    return {"filename": image.filename, "text": text}


@app.post("/api/v1/bulk_extract_text")
# extract multi images
async def bulk_extract_text(request: Request, bg_task: BackgroundTasks):
    images = await request.form()
    folder_name = str(uuid.uuid4())  # tạo folder with unique name
    os.mkdir(folder_name)

    for image in images.values():
        temp_file = _save_file_to_disk(image, path=folder_name, save_as=image.filename)

    bg_task.add_task(ocr.read_images_from_dir, folder_name, write_to_file=True)
    return {"task_id": folder_name, "num_files": len(images)}


@app.get("/api/v1/bulk_output/{task_id}")
# lấy output của extract multi images
async def bulk_output(task_id):
    text_map = {}
    for file_ in os.listdir(task_id):
        if file_.endswith("txt"):
            text_map[file_] = open(os.path.join(task_id, file_)).read()
    return {"task_id": task_id, "output": text_map}


def _save_file_to_disk(uploaded_file, path=".", save_as="default"):
    extension = os.path.splitext(uploaded_file.filename)[-1]
    temp_file = os.path.join(path, save_as + extension)
    with open(temp_file, "wb") as buffer:
        shutil.copyfileobj(uploaded_file.file, buffer)
    return temp_file
