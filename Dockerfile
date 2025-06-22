# Naudojame oficialų Python atvaizdą. Galite pasirinkti konkrečią versiją, pvz., python:3.10-slim-buster
FROM python:3.10-slim-buster

# Nustatome darbinį katalogą
WORKDIR /app

# Kopijuojame requirements.txt ir diegiame priklausomybes
# Šis žingsnis yra atskirtas, kad būtų galima pasinaudoti Docker sluoksniavimu ir talpykla
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopijuojame likusius failus į konteinerį
COPY . .

# Įdiegiame ffmpeg (jei jo nėra baziniame atvaizde)
# daugelis slim-buster atvaizdų neturi, todėl tai yra gera apsauga
RUN apt-get update && apt-get install -y ffmpeg

# Komanda, kuri paleidžiama paleidus konteinerį
# Tai pakeičia Procfile.
CMD ["python", "bot.py"]
