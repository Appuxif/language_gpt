# Language GPT

Telegram Бот заучивания английских слов в игровой форме.  
Пользователь создает списки из слов, которые хочет заучить, в интерфейсе бота.
Он может прослушать звучание этих слов, сгенерированное через `Google Text-To-Speech`.
В процессе игры для заучивания слов бот формирует примеры использования каждого слова
и проверяет предложенный пользователем перевод на ошибки через ChatGPT.

https://t.me/eng2learnbot


## Deploy

1. Copy ENV:  
    > cp .env-dev .env  
2. Change ENV values:  
    > vim .env
3. Run docker:  
    > sudo docker-compose up --build -d
