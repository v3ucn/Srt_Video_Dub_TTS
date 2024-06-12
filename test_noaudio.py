# 给定的元组
args = ('http://localhost:9880/', './Keira.wav', '光动嘴不如亲自做给你看,等我一下呀', '1.0')

# 确保提供的值与解包的变量数量相匹配
if len(args) == 4:
    gsv_url, gsv_wav, gsv_text_pro, gsv_speed = args
    print(gsv_url)
    print(gsv_wav)
    print(gsv_text_pro)
    print(gsv_speed)
else:
    print("提供的值数量与解包的变量数量不匹配")