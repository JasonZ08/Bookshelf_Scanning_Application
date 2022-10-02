# This file was generated by the Tkinter Designer by Parth Jadhav
# https://github.com/ParthJadhav/Tkinter-Designer


from pathlib import Path

# from tkinter import *
# Explicit imports to satisfy Flake8
from tkinter import Tk, Canvas, Entry, Text, Button, PhotoImage, messagebox
from tkinter import filedialog
import cv2
import tkinter as tk
from PIL import Image, ImageTk
import argparse
import os
import sys
from pathlib import Path
import torch
import torch.backends.cudnn as cudnn
import numpy
from numpy import asarray
import pytesseract
import shutil
import requests
from bs4 import BeautifulSoup as bs

namehold = []
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
OUTPUT_PATH = Path(__file__).parent
ASSETS_PATH = OUTPUT_PATH / Path("./assets")
count = 0
filename = ''
FILE = Path(__file__).resolve()
ROOT = FILE.parents[0]  # YOLOv5 root directory
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))  # add ROOT to PATH
ROOT = Path(os.path.relpath(ROOT, Path.cwd()))  # relative

from models.common import DetectMultiBackend
from utils.datasets import IMG_FORMATS, VID_FORMATS, LoadImages, LoadStreams
from utils.general import (LOGGER, check_file, check_img_size, check_imshow, check_requirements, colorstr,
                           increment_path, non_max_suppression, print_args, scale_coords, strip_optimizer, xyxy2xywh)
from utils.plots import Annotator, colors, save_one_box
from utils.torch_utils import select_device, time_sync

@torch.no_grad()
def run(weights=ROOT / 'yolov5x.pt',  # model.pt path(s)
        source=ROOT / 'data/images',  # file/dir/URL/glob, 0 for webcam
        imgsz=(640, 640),  # inference size (height, width)
        conf_thres=0.1,  # confidence threshold
        iou_thres=0.45,  # NMS IOU threshold
        max_det=1000,  # maximum detections per image
        device='',  # cuda device, i.e. 0 or 0,1,2,3 or cpu
        view_img=False,  # show results
        save_txt=True,  # save results to *.txt
        save_conf=False,  # save confidences in --save-txt labels
        save_crop=True,  # save cropped prediction boxes
        nosave=False,  # do not save images/videos
        classes=None,  # filter by class: --class 0, or --class 0 2 3
        agnostic_nms=False,  # class-agnostic NMS
        augment=False,  # augmented inference
        visualize=False,  # visualize features
        update=False,  # update all models
        project=ROOT / 'runs/detect',  # save results to project/name
        name='exp',  # save results to project/name
        exist_ok=False,  # existing project/name ok, do not increment
        line_thickness=3,  # bounding box thickness (pixels)
        hide_labels=False,  # hide labels
        hide_conf=False,  # hide confidences
        half=False,  # use FP16 half-precision inference
        dnn=False,  # use OpenCV DNN for ONNX inference
        ):

    source = str(source)
    save_img = not nosave and not source.endswith('.txt')  # save inference images
    is_file = Path(source).suffix[1:] in (IMG_FORMATS + VID_FORMATS)
    is_url = source.lower().startswith(('rtsp://', 'rtmp://', 'http://', 'https://'))
    webcam = source.isnumeric() or source.endswith('.txt') or (is_url and not is_file)
    if is_url and is_file:
        source = check_file(source)  # download

    # Directories
    save_dir = increment_path(Path(project) / name, exist_ok=exist_ok)  # increment run
    (save_dir / 'labels' if save_txt else save_dir).mkdir(parents=True, exist_ok=True)  # make dir

    # Load model
    device = select_device(device)
    model = DetectMultiBackend(weights, device=device, dnn=dnn)
    stride, names, pt, jit, onnx, engine = model.stride, model.names, model.pt, model.jit, model.onnx, model.engine
    global namehold
    namehold = names
    imgsz = check_img_size(imgsz, s=stride)  # check image size

    # Half
    half &= (pt or jit or engine) and device.type != 'cpu'  # half precision only supported by PyTorch on CUDA
    if pt or jit:
        model.model.half() if half else model.model.float()

    # Dataloader
    if webcam:
        view_img = check_imshow()
        cudnn.benchmark = True  # set True to speed up constant image size inference
        dataset = LoadStreams(source, img_size=imgsz, stride=stride, auto=pt)
        bs = len(dataset)  # batch_size
    else:
        dataset = LoadImages(source, img_size=imgsz, stride=stride, auto=pt)
        bs = 1  # batch_size
    vid_path, vid_writer = [None] * bs, [None] * bs

    # Run inference
    model.warmup(imgsz=(1, 3, *imgsz), half=half)  # warmup
    dt, seen = [0.0, 0.0, 0.0], 0
    for path, im, im0s, vid_cap, s in dataset:
        t1 = time_sync()
        im = torch.from_numpy(im).to(device)
        im = im.half() if half else im.float()  # uint8 to fp16/32
        im /= 255  # 0 - 255 to 0.0 - 1.0
        if len(im.shape) == 3:
            im = im[None]  # expand for batch dim
        t2 = time_sync()
        dt[0] += t2 - t1

        # Inference
        visualize = increment_path(save_dir / Path(path).stem, mkdir=True) if visualize else False
        pred = model(im, augment=augment, visualize=visualize)
        t3 = time_sync()
        dt[1] += t3 - t2

        # NMS
        pred = non_max_suppression(pred, conf_thres, iou_thres, classes, agnostic_nms, max_det=max_det)
        dt[2] += time_sync() - t3

        # Second-stage classifier (optional)
        # pred = utils.general.apply_classifier(pred, classifier_model, im, im0s)

        # Process predictions
        for i, det in enumerate(pred):  # per image
            seen += 1
            if webcam:  # batch_size >= 1
                p, im0, frame = path[i], im0s[i].copy(), dataset.count
                s += f'{i}: '
            else:
                p, im0, frame = path, im0s.copy(), getattr(dataset, 'frame', 0)

            p = Path(p)  # to Path
            save_path = str(save_dir / p.name)  # im.jpg
            txt_path = str(save_dir / 'labels' / p.stem) + ('' if dataset.mode == 'image' else f'_{frame}')  # im.txt
            s += '%gx%g ' % im.shape[2:]  # print string
            gn = torch.tensor(im0.shape)[[1, 0, 1, 0]]  # normalization gain whwh
            imc = im0.copy() if save_crop else im0  # for save_crop
            annotator = Annotator(im0, line_width=line_thickness, example=str(names))
            if len(det):
                # Rescale boxes from img_size to im0 size
                det[:, :4] = scale_coords(im.shape[2:], det[:, :4], im0.shape).round()

                # Print results
                for c in det[:, -1].unique():
                    n = (det[:, -1] == c).sum()  # detections per class
                    s += f"{n} {names[int(c)]}{'s' * (n > 1)}, "  # add to string

                # Write results
                for *xyxy, conf, cls in reversed(det):
                    if save_txt:  # Write to file
                        xywh = (xyxy2xywh(torch.tensor(xyxy).view(1, 4)) / gn).view(-1).tolist()  # normalized xywh
                        line = (cls, *xywh, conf) if save_conf else (cls, *xywh)  # label format
                        with open(txt_path + '.txt', 'a') as f:
                            f.write(('%g ' * len(line)).rstrip() % line + '\n')

                    if save_img or save_crop or view_img:  # Add bbox to image
                        c = int(cls)  # integer class
                        label = None if hide_labels else (names[c] if hide_conf else f'{names[c]} {conf:.2f}')
                        annotator.box_label(xyxy, label, color=colors(c, True))
                        if save_crop:
                            save_one_box(xyxy, imc, file=save_dir / 'crops' / names[c] / f'{p.stem}.jpg', BGR=True)

            # Print time (inference-only)
            LOGGER.info(f'{s}Done. ({t3 - t2:.3f}s)')

            # Stream results
            im0 = annotator.result()
            if view_img:
                cv2.imshow(str(p), im0)
                cv2.waitKey(1)  # 1 millisecond

            # Save results (image with detections)
            if save_img:
                if dataset.mode == 'image':
                    cv2.imwrite(save_path, im0)
                else:  # 'video' or 'stream'
                    if vid_path[i] != save_path:  # new video
                        vid_path[i] = save_path
                        if isinstance(vid_writer[i], cv2.VideoWriter):
                            vid_writer[i].release()  # release previous video writer
                        if vid_cap:  # video
                            fps = vid_cap.get(cv2.CAP_PROP_FPS)
                            w = int(vid_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                            h = int(vid_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        else:  # stream
                            fps, w, h = 30, im0.shape[1], im0.shape[0]
                            save_path += '.mp4'
                        vid_writer[i] = cv2.VideoWriter(save_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
                    vid_writer[i].write(im0)
            return im0

    # Print results
    t = tuple(x / seen * 1E3 for x in dt)  # speeds per image
    LOGGER.info(f'Speed: %.1fms pre-process, %.1fms inference, %.1fms NMS per image at shape {(1, 3, *imgsz)}' % t)
    if save_txt or save_img:
        s = f"\n{len(list(save_dir.glob('labels/*.txt')))} labels saved to {save_dir / 'labels'}" if save_txt else ''
        LOGGER.info(f"Results saved to {colorstr('bold', save_dir)}{s}")
    if update:
        strip_optimizer(weights)  # update model (to fix SourceChangeWarning)



def relative_to_assets(path: str) -> Path:
    return ASSETS_PATH / Path(path)


def onFrameConfigure(canvas):
    '''Reset the scroll region to encompass the inner frame'''
    canvas.configure(scrollregion=canvas.bbox("all"))

def openFile():
    canvasUpload.delete('chosen')
    canvasUpload.delete('back')
    canvasUpload.delete('search')
    canvasUpload.delete('result')
    global coordArray
    global myBookPic
    top = 50
    left = 100
    right = 900
    bottom = 650
    filename = filedialog.askopenfilename(title='"pen')
    img1 = Image.open(filename)  # input image
    cv2image = cv2.cvtColor(numpy.array(img1), cv2.COLOR_RGB2BGR)
    os.chdir(r"C:\Users\j2011\Documents\YOLO Tkinter\yolov5\data\images")
    cv2.imwrite("snap.jpg", cv2image)
    os.chdir(r"C:")
    location = "C:/Users/j2011/Documents/YOLO Tkinter/yolov5/runs\detect/"
    dir = "exp"
    path = os.path.join(location, dir)
    shutil.rmtree(path)
    os.chdir(r"C:\Users\j2011\Documents\YOLO Tkinter\yolov5")
    immmmm = run()
    img = cv2.cvtColor(immmmm, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(img)
    img2 = ImageTk.PhotoImage(img)
    if img2.height() > 600 and img2.width() > 800:
        img = img.resize((800, 600), Image.ANTIALIAS)
    elif img2.height() > 600:
        img = img.resize((img2.width(), 600), Image.ANTIALIAS)
    elif img2.width() > 800:
        img = img.resize((800, img2.height()), Image.ANTIALIAS)
    img = ImageTk.PhotoImage(img)
    myBookPic = img
    #img = img.resize((300, 300), Image.ANTIALIAS)  # resize image
    #print(img.height())
    #print(img.width())
    imagecu = canvasUpload.create_image((500, 350), image=img, anchor='center', tag = 'InitialScan')
    #imagecu_window = canvasUpload.create_window(500, 400, anchor = 'center', window = img)
    canvasUpload.image = img
    coordArray = []
    os.chdir(r"C:\Users\j2011\Documents\YOLO Tkinter\yolov5\runs\detect\exp\labels")
    f = open('snap.txt')
    mydict = {}
    for line in f:
        temp = line.split(' ')
        temp[4] = temp[4][:-1]
        temp[1] = float(temp[1]) * img.width()
        temp[2] = float(temp[2]) * img.height()
        temp[3] = float(temp[3]) * img.width()
        temp[4] = float(temp[4]) * img.height()
        if temp[0] not in mydict:
            mydict[temp[0]] = 0
        mydict[temp[0]] += 1
        temp.append(mydict[temp[0]])
        coordArray.append(temp)
    canvasUpload.bind("<Button 1>", motion)

def back():
    global myBookPic
    canvasUpload.delete('chosen')
    canvasUpload.delete('back')
    canvasUpload.delete('search')
    canvasUpload.delete('result')
    imagecu = canvasUpload.create_image((500, 350), image=myBookPic, anchor='center', tag='InitialScan')
    canvasUpload.image = myBookPic
    canvasUpload.bind("<Button 1>", motion)

def motion(event):
    global coordArray
    x, y = event.x, event.y
    possBox = []
    for z in coordArray:
        x1, y1, width, height = z[1], z[2], z[3], z[4]
        if (x1 - width / 2) + 100 < x < (x1 + width / 2) + 100 and (y1 - height / 2)  + 50 < y < (y1 + height / 2) + 50:
            possBox.append(z)
    if possBox:
        displayPic(possBox[0])
    #print('{}, {}'.format(x, y))

def displayPic(myNum):
    def search():
        canvasUpload.delete('search')
        myText = titleText.get("1.0", 'end-1c')
        page = requests.get("https://google.com/search?tbm=bks&q=" + myText)
        soup = bs(page.text, "html.parser")

        temp = None
        links = soup.findAll("a")
        for link in links:
            link_thing = link.get("href")
            if "books.google.com" in link_thing:
                temp = link_thing
                print(link_thing)
                break

        page = requests.get(temp)
        soup = bs(page.text, "html.parser")
        temp = None
        links = soup.findAll("a")
        for link in links:
            link_thing = link.get("href")
            if "https://www.google.com/books/" in link_thing:
                temp = link_thing[0:link_thing.index("=en&") + 4] + "gbpv=0"
                print(temp)
                break

        page = requests.get(temp)
        soup = bs(page.text, "html.parser")
        temp = None
        description = soup.find("div", {"id": "synopsis"})
        print(description.text)
        canvasUpload.create_text(250, 50, text = 'Description:', font = ("Arial", 15), anchor = 'nw', tag = 'result')
        canvasUpload.create_text(250, 100, text=description.text, font=("Arial", 10), anchor='nw',
                                 tag='result', width = 600)

    canvasUpload.unbind("<Button 1>")
    #myNum[4] = myNum[4][:-1]
    os.chdir(r"C:\Users\j2011\Documents\YOLO Tkinter\yolov5\runs\detect\exp\crops/" + namehold[int(myNum[0])])
    #os.chdir(r"C:\Users\j2011\Documents\YOLO Tkinter\yolov5\runs\detect\exp\crops/" + namehold[int(myNum)])
    if myNum[-1] ==1:
        cv2image = cv2.cvtColor(cv2.imread("snap.jpg"), cv2.COLOR_BGR2RGB)
    else:
        cv2image = cv2.cvtColor(cv2.imread("snap" + str(myNum[-1]) + ".jpg"), cv2.COLOR_BGR2RGB)

    #cv2image = cv2.cvtColor(cv2.imread("snap" + str(13) + ".jpg"), cv2.COLOR_BGR2RGB)
    hImg, wImg, _ = cv2image.shape
    boxes = pytesseract.image_to_data(cv2image)
    myTitle = ''
    for x, b in enumerate(boxes.splitlines()):
        if x != 0:
            b = b.split()
            #print(b)
            if len(b) == 12:
                x, y, w, h = int(b[6]), int(b[7]), int(b[8]), int(b[9])
                cv2.rectangle(cv2image, (x, y), (w + x, h + y), (170, 255, 0), 1)
                cv2.putText(cv2image, b[11], (x, y), cv2.FONT_HERSHEY_COMPLEX, 0.5, (170, 255, 0),
                            1)  # the 0.5 is font size, 1
                myTitle += (b[11] + ' ')
    img = Image.fromarray(cv2image)
    img2 = ImageTk.PhotoImage(img)
    if img2.height() > 600 and img2.width() > 800:
        img = img.resize((800, 600), Image.ANTIALIAS)
    elif img2.height() > 600:
        img = img.resize((img2.width(), 600), Image.ANTIALIAS)
    elif img2.width() > 800:
        img = img.resize((800, img2.height()), Image.ANTIALIAS)
    imgtk = ImageTk.PhotoImage(image=img)
    canvasUpload.delete('InitialScan')
    canvasUpload.create_image((125, 350), image=imgtk, anchor='center', tag = 'chosen')
    canvasUpload.image = imgtk
    textName4b = tk.StringVar()
    button4b = tk.Button(root2, textvariable=textName4b, font='Raleway', height=1, width=15, command=back)
    textName4b.set("Back")
    button4b_window = canvasUpload.create_window(1000, 350, anchor='nw', window=button4b, tag='back')
    canvasUpload.create_text(600, 50, text = 'Is This Information Right?', font = ("Arial", 30), anchor = 'center', tag = 'search')
    canvasUpload.create_text(600, 100, text='Edit If Needed', font=("Arial", 20), anchor='center', tag='search')
    canvasUpload.create_text(300, 175, text='Title:', font=("Arial", 20), anchor='nw', tag='search')
    #canvasUpload.create_text(300, 250, text='Author:', font=("Arial", 22), anchor='nw',tag='back')
    titleText = tk.Text(root2, height = 3, width = 50)
    titleText.insert(tk.END, myTitle)
    canvasUpload.create_window(425, 175, anchor = 'nw', window = titleText, tag='search')
    #authorText = tk.Text(root2, height=3, width=50)
    #canvasUpload.create_window(450, 250, anchor='nw', window=authorText, tag='back')
    buttonSub = tk.Button(root2, text = 'Submit', font='Raleway', height=1, width=15, command = search)
    canvasUpload.create_window(600, 275, anchor = 'center', window = buttonSub, tag = 'search')

def newWindow():
    global count
    window.destroy()
    count += 1

def populate(frame):
    os.chdir(r"C:\Users\j2011\Documents\YOLO Tkinter\yolov5\runs\detect\exp\labels")
    f = open('snap.txt')
    count = 0
    myButtons = []
    mydict = {}
    for line in f:
        temp = line.split(' ')
        if temp[0] not in mydict:
            mydict[temp[0]] = 0
        mydict[temp[0]] += 1
        temp.append(mydict[temp[0]])
        s = tk.Button(frame, width=52, height = 2, text = namehold[int(temp[0])] + str(mydict[temp[0]]), command = lambda x = temp: displayPic(x)).grid(row=count, column=0)
        myButtons.append(s)
        count+=1

def newWindow2():
    global count
    global after_id
    root.after_cancel(after_id)
    root.destroy()
    count = 2

def newWindow3():
    global count
    global after_id
    root.after_cancel(after_id)
    count = 3
    root.destroy()

def show_frames():
    global after_id
    cv2image = cv2.cvtColor(cap.read()[1], cv2.COLOR_BGR2RGB)
    img = Image.fromarray(cv2image)
    imgtk = ImageTk.PhotoImage(image=img)
    label1.imgtk = imgtk
    label1.configure(image=imgtk)
    after_id = root.after(20, show_frames)


def printState():
    cv2image = cv2.cvtColor(cap.read()[1], cv2.COLOR_BGR2RGB)
    img = Image.fromarray(cv2image)
    os.chdir(r"C:\Users\j2011\Documents\YOLO Tkinter\yolov5\data\images")
    cv2.imwrite("snap.jpg", cv2image)
    os.chdir(r"C:")
    location = "C:/Users/j2011/Documents/YOLO Tkinter/yolov5/runs\detect/"
    dir = "exp"
    path = os.path.join(location, dir)
    shutil.rmtree(path)
    os.chdir(r"C:\Users\j2011\Documents\YOLO Tkinter\yolov5")
    immmmm = run()
    img = Image.fromarray(immmmm)
    img2 = ImageTk.PhotoImage(img)
    if img2.height() > 600 and img2.width() > 800:
        img = img.resize((800, 600), Image.ANTIALIAS)
    elif img2.height() > 600:
        img = img.resize((img2.width(), 600), Image.ANTIALIAS)
    elif img2.width() > 800:
        img = img.resize((800, img2.height()), Image.ANTIALIAS)
    img = ImageTk.PhotoImage(img)
    canvasUpload3.create_image((500, 350), image=img, anchor='center', tag = 'InitialScan')
    canvasUpload3.image = img



def retake():
    global count
    root3.destroy()
    count = 1

def on_closing():
    root.destroy()

def on_closing2():
    root2.destroy()

def on_closing3():
    root3.destroy()

if count == 0:
    window = Tk()

    window.geometry("900x600")
    window.configure(bg="#FFFFFF")

    canvas = Canvas(
        window,
        bg="#FFFFFF",
        height=600,
        width=900,
        bd=0,
        highlightthickness=0,
        relief="ridge"
    )

    canvas.place(x=0, y=0)
    image_image_1 = PhotoImage(
        file=relative_to_assets("image_1.png"))
    image_1 = canvas.create_image(
        450.0,
        300.0,
        image=image_image_1
    )

    canvas.create_text(
        387.0,
        24.0,
        anchor="nw",
        text="Book Scanner",
        fill="#000000",
        font=("Roboto Bold", 30 * -1)
    )

    canvas.create_text(
        428.0,
        119.0,
        anchor="nw",
        text="Welcome to Book",
        fill="#FFFFFF",
        font=("Roboto", 48 * -1)
    )

    canvas.create_text(
        527.0,
        175.0,
        anchor="nw",
        text="Scanner",
        fill="#FFFFFF",
        font=("Roboto", 48 * -1)
    )

    button_image_1 = PhotoImage(
        file=relative_to_assets("button_1.png"))
    button_1 = Button(
        image=button_image_1,
        borderwidth=0,
        highlightthickness=0,
        command=lambda: newWindow(),
        relief="flat"
    )
    button_1.place(
        x=467.0,
        y=307.0,
        width=295.0,
        height=60.0
    )

    canvas.create_text(
        482.0,
        248.0,
        anchor="nw",
        text="A free, easy, and reliable program",
        fill="#FFFFFF",
        font=("Roboto", 18 * -1)
    )

    canvas.create_text(
        548.0,
        269.0,
        anchor="nw",
        text="to identify books",
        fill="#FFFFFF",
        font=("Roboto", 18 * -1)
    )

    canvas.create_text(
        796.0,
        30.0,
        anchor="nw",
        text="Hello User!",
        fill="#0071E0",
        font=("Roboto Light", 16 * -1)
    )
    window.resizable(False, False)
    window.mainloop()

if count == 1:
    root = tk.Tk()
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.columnconfigure(0, minsize=600)
    root.rowconfigure(0, minsize=300)
    root.rowconfigure(1, minsize=100)
    label1 = tk.Label()
    label1.grid(row=0, column=0, stick='nsew')
    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    print(cap)
    label2 = tk.Label()
    frame1 = tk.Frame(root)
    frame2 = tk.Frame(root)

    show_frames()
    textName = tk.StringVar()
    button = tk.Button(frame1, textvariable=textName, font='Raleway', height=1, width=15, command=newWindow3)
    textName.set("Snapshot")

    textName3 = tk.StringVar()
    button3 = tk.Button(frame1, textvariable=textName3, font='Raleway', height=1, width=15, command=on_closing)
    textName3.set("Quit")
    button.pack(side='left', padx=10)
    button3.pack(side='right', padx=10)

    textName4 = tk.StringVar()
    button6 = tk.Button(frame1, textvariable=textName4, font='Raleway', height=1, width=15,
                        command=lambda: newWindow2())
    button6.pack(padx=10)
    textName4.set("Image Upload")

    frame1.grid(row=1, column=0)
    cv2.destroyAllWindows()
    root.mainloop()

if count == 2:
    root2 = tk.Tk()
    root2.protocol("WM_DELETE_WINDOW", on_closing)
    canvasUpload = Canvas(root2, width = 1200, height = 700)
    canvasUpload.pack()

    os.chdir(r"C:\Users\j2011\Documents")
    bg = Image.open('pinkBackground.jpg')
    bg = ImageTk.PhotoImage(bg)
    canvasUpload.create_image(0, 0, image=bg,
                         anchor="nw")

    textName1 = tk.StringVar()
    button1up = tk.Button(root2, textvariable=textName1, font='Raleway', height=1, width=15, command=openFile)
    button1_window = canvasUpload.create_window(1000, 100, anchor = 'nw', window = button1up)
    textName1.set("Choose a File")

    textName3 = tk.StringVar()
    button3up = tk.Button(root2, textvariable=textName3, font='Raleway', height=1, width=15, command=on_closing2)
    textName3.set("Quit")
    button3_window = canvasUpload.create_window(1000, 600, anchor='nw', window=button3up)
    root2.mainloop()

elif count == 3:
    root3 = tk.Tk()
    root3.protocol("WM_DELETE_WINDOW", on_closing)
    canvasUpload3 = Canvas(root3, width=1200, height=700)
    canvasUpload3.pack()

    os.chdir(r"C:\Users\j2011\Documents")
    bg = Image.open('pinkBackground.jpg')
    bg = ImageTk.PhotoImage(bg)
    canvasUpload3.create_image(0, 0, image=bg,
                              anchor="nw")

    textName1 = tk.StringVar()
    button13 = tk.Button(root3, textvariable=textName1, font='Raleway', height=1, width=15, command=retake)
    button13_window = canvasUpload3.create_window(1000, 100, anchor = 'nw', window = button13)
    textName1.set("Retake")

    textName3 = tk.StringVar()
    button33 = tk.Button(root3, textvariable=textName3, font='Raleway', height=1, width=15, command=on_closing3)
    textName3.set("Quit")
    button33_window = canvasUpload3.create_window(1000, 600, anchor='nw', window=button33)

    printState()
    root3.mainloop()



