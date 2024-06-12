
from moviepy.editor import VideoFileClip

import os

import ffmpeg

from faster_whisper import WhisperModel
import math

import torch

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM,pipeline


device = "cuda" if torch.cuda.is_available() else "cpu"



# 合并字幕
def merge_sub(video_path,srt_path):

    if os.path.exists("./test_srt.mp4"):
        os.remove("./test_srt.mp4")

    ffmpeg.input(video_path).output("./test_srt.mp4", vf="subtitles=" + srt_path).run()

    return "./test_srt.mp4"



def convert_seconds_to_hms(seconds):
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = math.floor((seconds % 1) * 1000)
    output = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02},{milliseconds:03}"
    return output

# 制作字幕文件
def make_srt(file_path,model_name="small"):

    print(file_path)

    
    # if device == "cuda":
    #     model = WhisperModel(model_name, device="cuda", compute_type="float16",download_root="./model_from_whisper",local_files_only=False)
    # else:
    #     model = WhisperModel(model_name, device="cpu", compute_type="int8",download_root="./model_from_whisper",local_files_only=False)
    # or run on GPU with INT8
    # model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")
        
    if device == "cuda":
        try:
            model = WhisperModel(model_name, device="cuda", compute_type="float16",download_root="./model_from_whisper",local_files_only=False)
        except Exception as e:
            model = WhisperModel(model_name, device="cuda", compute_type="int8_float16",download_root="./model_from_whisper",local_files_only=False)
    else:
        model = WhisperModel(model_name, device="cpu", compute_type="int8",download_root="./model_from_whisper",local_files_only=False)

    segments, info = model.transcribe(file_path, beam_size=5,vad_filter=True,vad_parameters=dict(min_silence_duration_ms=500))

    print("Detected language '%s' with probability %f" % (info.language, info.language_probability))
    count = 0
    with open('./video.srt', 'w',encoding="utf-8") as f:  # Open file for writing
        for segment in segments:
            count +=1
            duration = f"{convert_seconds_to_hms(segment.start)} --> {convert_seconds_to_hms(segment.end)}\n"
            text = f"{segment.text.lstrip()}\n\n"
            
            f.write(f"{count}\n{duration}{text}")  # Write formatted string to the file
            print(f"{duration}{text}",end='')

    with open("./video.srt","r",encoding="utf-8") as f:
        content = f.read()

    return content



# 提取人声
def movie2audio(video_path):

    # 读取视频文件
    video = VideoFileClip(video_path)

    # 提取视频文件中的声音
    audio = video.audio

    # 将声音保存为WAV格式
    audio.write_audiofile("./audio.wav")

    ans = pipeline_ali(
        Tasks.acoustic_noise_suppression,
        model=model_dir_cirm)
    
    ans('./audio.wav',output_path='./output.wav')

    return "./output.wav"

class subtitle:
    def __init__(self,index:int, start_time, end_time, text:str):
        self.index = int(index)
        self.start_time = start_time
        self.end_time = end_time
        self.text = text.strip()
    def normalize(self,ntype:str,fps=30):
         if ntype=="prcsv":
              h,m,s,fs=(self.start_time.replace(';',':')).split(":")#seconds
              self.start_time=int(h)*3600+int(m)*60+int(s)+round(int(fs)/fps,2)
              h,m,s,fs=(self.end_time.replace(';',':')).split(":")
              self.end_time=int(h)*3600+int(m)*60+int(s)+round(int(fs)/fps,2)
         elif ntype=="srt":
             h,m,s=self.start_time.split(":")
             s=s.replace(",",".")
             self.start_time=int(h)*3600+int(m)*60+round(float(s),2)
             h,m,s=self.end_time.split(":")
             s=s.replace(",",".")
             self.end_time=int(h)*3600+int(m)*60+round(float(s),2)
         else:
             raise ValueError
    def add_offset(self,offset=0):
        self.start_time+=offset
        if self.start_time<0:
            self.start_time=0
        self.end_time+=offset
        if self.end_time<0:
            self.end_time=0
    def __str__(self) -> str:
        return f'id:{self.index},start:{self.start_time},end:{self.end_time},text:{self.text}'


def read_srt(file,offset=0):
    with open('./newsrt.srt','w',encoding='utf-8') as f:
        f.write(file)
    with open("./newsrt.srt","r",encoding="utf-8") as f:
        file=f.readlines()

    subtitle_list=[]
    indexlist=[]
    filelength=len(file)
    for i in range(0,filelength):
        if " --> " in file[i]:
            is_st=True
            for char in file[i-1].strip().replace("\ufeff",""):
                if char not in ['0','1','2','3','4','5','6','7','8','9']:
                    is_st=False
                    break
            if is_st:
                indexlist.append(i) #get line id
    listlength=len(indexlist)
    for i in range(0,listlength-1):
        st,et=file[indexlist[i]].split(" --> ")
        id=int(file[indexlist[i]-1].strip().replace("\ufeff",""))
        text=""
        for x in range(indexlist[i]+1,indexlist[i+1]-2):
            text+=file[x]
        st=subtitle(id,st,et,text)
        st.normalize(ntype="srt")
        st.add_offset(offset=offset)
        subtitle_list.append(st)

    st,et=file[indexlist[-1]].split(" --> ")
    id=file[indexlist[-1]-1]
    text=""
    for x in range(indexlist[-1]+1,filelength):
        text+=file[x]
    st=subtitle(id,st,et,text)
    st.normalize(ntype="srt")
    st.add_offset(offset=offset)
    subtitle_list.append(st)
    return subtitle_list





