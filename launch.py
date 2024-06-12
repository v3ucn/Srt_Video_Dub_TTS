# -*- encoding: utf-8 -*-

import os
import gradio as gr
import librosa
import datetime
import time
import subprocess
import concurrent.futures

import ffmpeg

import sys

from utils import make_srt,read_srt

import soundfile as sf

import requests

import numpy as np

import json

from moviepy.editor import VideoFileClip,AudioFileClip



initial_md = """


webui作者：刘悦的技术博客  https://space.bilibili.com/3031494

"""


def gsv_change_model(url,gptmodel,sovitsmodel):

    requests.get(f"{url}set_gpt_weights?weights_path={gptmodel}")
    requests.get(f"{url}set_sovits_weights?weights_path={sovitsmodel}")





def merge_video(video_path,audio_path):

    # 定义输入视频文件和输出视频文件
    input_video = video_path
    output_video_silent = "./noaudio.mp4"

    # 加载视频剪辑
    video_clip = VideoFileClip(input_video)

    # 检查视频是否包含音频
    if video_clip.audio is not None:
        # 如果视频包含音频，则去除音频并保存为无声视频
        video_clip = video_clip.set_audio(None)
        video_clip.write_videofile(output_video_silent, codec='libx264', audio=False)
        print("已保存无声视频")
    else:
        # 如果视频本身就没有音频，则直接保存为无声视频
        video_clip.write_videofile(output_video_silent, codec='libx264', audio=False)
        print("已保存无声视频")

    # 关闭视频剪辑
    video_clip.close()

        # 读取视频文件和音频文件
    videoclip = VideoFileClip("./noaudio.mp4")
    audioclip = AudioFileClip("./audio.wav")

    # 将音频与视频合并
    videoclip = videoclip.set_audio(audioclip)

    # 保存合并后的视频文件
    videoclip.write_videofile("./newvideo.mp4")

    videoclip.close()
    audioclip.close()

    return "./newvideo.mp4"

def merge_video_srt(video_path):

    if os.path.exists("./test_srt.mp4"):
        os.remove("./test_srt.mp4")

    ffmpeg.input("./newvideo.mp4").output("./test_srt.mp4", vf="subtitles=" + "./newsrt.srt").run()

    return "./test_srt.mp4"



def file_show(file):
    if file is None:
        return ""
    try:
      with open(file.name, "r", encoding="utf-8") as f:
         text = f.read()
      return text
    except Exception as error:
        return error


def save(args,proj:str=None,text:str=None,dir:str=None,subid:int=None):
    if proj=="gsv":
        print("测试")
        print(args)
        print(type(args))
        # 确保提供的值与解包的变量数量相匹配
        gsv_url, gsv_wav, gsv_text_pro, gsv_speed = args

        headers = {'Content-Type': 'application/json'}
        
        gpt = {"text":text,"text_lang":"zh","ref_audio_path":gsv_wav,"prompt_lang":"zh","prompt_text":gsv_text_pro,"text_split_method":"cut5","batch_size":5,"speed_factor":float(gsv_speed)}

        res = requests.post(gsv_url,data=json.dumps(gpt),headers=headers)

        audio = res.content
    elif proj=="bert":

        print("测试")
        print(args)
        print(type(args))
        # 确保提供的值与解包的变量数量相匹配
        gsv_url = args[0]

        headers = {'Content-Type': 'application/json'}
        
        gpt = {"text":text}

        res = requests.post(gsv_url,data=json.dumps(gpt),headers=headers)

        audio = res.content

    elif proj=="chat":

        print("测试")
        print(args)
        print(type(args))
        # 确保提供的值与解包的变量数量相匹配
        gsv_url,seed = args

        headers = {'Content-Type': 'application/json'}
        
        gpt = {"text":text,"seed":seed}

        res = requests.post(gsv_url,data=json.dumps(gpt),headers=headers)

        audio = res.content




    filepath=os.path.join(dir,f"{subid}.wav")
    with open(filepath,'wb') as file:
        file.write(audio)
        return filepath


def before_gen_gsv(srt_text,proj,sr,gsv_url,gsv_wav,gsv_text_pro,gsv_speed):

    return gen_gsv(gsv_url,gsv_wav,gsv_text_pro,gsv_speed,srt_text=srt_text,proj=proj,sr=sr)


def before_gen_bert(srt_text,proj,sr,bert_url):

    return gen_gsv(bert_url,srt_text=srt_text,proj=proj,sr=sr)

def before_gen_chat(srt_text,proj,sr,bert_url,chat_seed):

    return gen_gsv(bert_url,chat_seed,srt_text=srt_text,proj=proj,sr=sr)


def gen_gsv(*args,srt_text,proj,sr):

    sr = int(sr)

    audiolist=[]
    subtitle_list=read_srt(srt_text)
    
    ptr=0
    t=datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    dirname="./tem"
    os.makedirs(dirname,exist_ok=True)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        file_list = list(executor.map(lambda x: save(x[0], **x[1]),[[args, {'proj': proj, 'text': i.text, 'dir': dirname, 'subid': i.index}] for i in subtitle_list]))

    file_list=[i for i in file_list if i is not None]
    for i in subtitle_list:
        start_frame=int(i.start_time*sr)
        if ptr<start_frame:
            silence_len=start_frame-ptr
            audiolist.append(np.zeros(silence_len))
            ptr+=silence_len
        elif ptr>start_frame:
            pass                  
        f_path=os.path.join(dirname,f"{i.index}.wav")
        if f_path in file_list:
            wav, _ = librosa.load(f_path, sr=sr)
            dur=wav.shape[-1]             #frames
            ptr+=dur
            audiolist.append(wav)
    audio=np.concatenate(audiolist)
    assert len(file_list)!=0,"api fucked"
    sf.write("./audio.wav", audio, sr)


    
    return (sr,audio)

if __name__ == "__main__":
    
    
    # gradio interface
    theme = gr.Theme.load("theme.json")
    with gr.Blocks(theme=theme) as demo:
        gr.Markdown(initial_md)

        video_state, audio_state = gr.State(), gr.State()
        with gr.Row():
            with gr.Column():
                with gr.Row():
                    video_input = gr.Video(label="(A0)上传视频 upload video")
                    audio_input = gr.Audio(label="(A0)上传音频 upload audio",type="filepath")
                
                recog_button = gr.Button("(B0)识别视频并且生成字幕", variant="primary")
                recog_button_audio = gr.Button("(B0)识别音频并且生成字幕", variant="primary")
                srt_file = gr.File(label="(B1)不需要识别直接上传字幕",file_types=['.srt'],file_count='single')

                video_srt_output = gr.Textbox(label="📖 SRT字幕内容 | RST Subtitles")
            with gr.Column():
                with gr.Tab("Gpt-SoVITS"):
                    with gr.Column():

                        gsv_url = gr.Textbox(label="接口地址",value="http://localhost:9880/")

                        gsv_gptmodel = gr.Textbox(label="gpt模型",value="GPT_weights/Keira-e15.ckpt")

                        gsv_sovitsmodel = gr.Textbox(label="sovits模型",value="SoVITS_weights/Keira_e8_s96.pth")

                        gsv_change_button = gr.Button("切换模型", variant="primary")

                        gsv_wav = gr.Textbox(label="参考音频地址",value="./Keira.wav")

                        gsv_text_pro = gr.Textbox(label="参考音频文本",value="光动嘴不如亲自做给你看,等我一下呀")

                        gsv_speed = gr.Textbox(label="语速",value="1.0")



                        gsv_button = gr.Button("(C0)请求GPT-SoVITS接口", variant="primary")

                        gsv_sr = gr.Textbox(value="32000",visible=False)

                        gsv_type = gr.Textbox(value="gsv",visible=False)


                with gr.Tab("ChatTTS"):
                    with gr.Column():

                        chat_url = gr.Textbox(label="接口地址",value="http://localhost:9880/")

                        chat_seed = gr.Textbox(label="角色种子",value="2581")


                        chat_button = gr.Button("(C0)请求ChatTTS接口", variant="primary")


                        chat_sr = gr.Textbox(value="16000",visible=False)

                        chat_type = gr.Textbox(value="chat",visible=False)


                with gr.Tab("Bert-Vits2"):
                    with gr.Column():

                        bert_url = gr.Textbox(label="接口地址",value="http://localhost:9885/")


                        bert_button = gr.Button("(C0)请求Bert-vits2接口", variant="primary")


                        bert_sr = gr.Textbox(value="44100",visible=False)

                        bert_type = gr.Textbox(value="bert",visible=False)

           


                
                

                audio_output = gr.Audio(label="语音合成结果 | output Audio ")

                merge_button = gr.Button("(D0)将合成的语音合并到新视频", variant="primary")

                merge_button_srt = gr.Button("(E0)将字幕合并到新视频(D0操作必须先完成)", variant="primary")

                video_output = gr.Video(label="视频合成结果 | output Video ")

        gsv_change_button.click(gsv_change_model,inputs=[gsv_url,gsv_gptmodel,gsv_sovitsmodel])
        
        gsv_button.click(before_gen_gsv, 
                            inputs=[video_srt_output,gsv_type,gsv_sr,gsv_url,gsv_wav,gsv_text_pro,gsv_speed],outputs=[audio_output])

        bert_button.click(before_gen_bert, 
                            inputs=[video_srt_output,bert_type,bert_sr,bert_url],outputs=[audio_output])

        chat_button.click(before_gen_chat, 
                            inputs=[video_srt_output,chat_type,chat_sr,chat_url,chat_seed],outputs=[audio_output])


        merge_button.click(merge_video, 
                            inputs=[video_input,audio_output],outputs=[video_output]) 

        merge_button_srt.click(merge_video_srt, 
                            inputs=[video_input],outputs=[video_output])         
                
        recog_button.click(make_srt, 
                            inputs=[video_input],outputs=[video_srt_output])

        recog_button_audio.click(make_srt, 
                            inputs=[audio_input],outputs=[video_srt_output])

        srt_file.change(file_show,inputs=[srt_file],outputs=[video_srt_output])
        
    
    # start gradio service in local
    demo.launch(inbrowser=True)
