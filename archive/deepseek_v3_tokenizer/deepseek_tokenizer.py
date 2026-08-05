# pip3 install transformers
# python3 deepseek_tokenizer.py
import transformers

chat_tokenizer_dir = "./"

tokenizer = transformers.AutoTokenizer.from_pretrained( 
        chat_tokenizer_dir, trust_remote_code=True
        )

result = tokenizer.encode("深度求索就是好！")
print(len(result))


import tiktoken
tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo-16k")
my_tokens = tokenizer.encode("深度求索就是好！")
print(len(my_tokens))

