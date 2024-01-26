import cv2
import re
import requests
import time
import pandas as pd
from bs4 import BeautifulSoup
from pyzbar.pyzbar import decode

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

def extraer_carrefour(producto):
    driver = webdriver.Chrome()

    driver.get(f'https://www.carrefour.es/?q={producto}')  #el driver accede al sitio web de carrefour con el producto buscado

    accept_cookies = driver.find_element(By.ID,'onetrust-accept-btn-handler')  #dentro de la web acepta las cookies
    accept_cookies.click()

    time.sleep(1) #espera 1s a que cargue la pagina
    soup = BeautifulSoup(driver.page_source, "html.parser") #convierte en sopa de html esa pagina
    productos = soup.find_all('h1',class_='ebx-result-title ebx-result__title') #busca los nombres de los productos
    precios= soup.find_all('p', class_='ebx-result-price ebx-result__price')  #busca los precios de los productos

    d={}
    driver.quit()
    for producto,precio in zip(productos,precios): #crea un diccionario de la forma {producto:precio}
        d[producto.text]=precio.text
    return d


def extraer_dia(producto):
    driver = webdriver.Chrome()
    driver.get(f'https://www.dia.es/search?q={producto}')
    time.sleep(1)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    productos = soup.find_all('p',class_='search-product-card__product-name')
    precios = soup.find_all('p',class_='search-product-card__active-price')

    d={}

    driver.quit()
    for producto,precio in zip(productos,precios):
        d[producto.text]=precio.text.replace('\xa0','')# se reemplaza el caracter del espacio
    return d
    

def descarte_marcas_blancas(texto, marca):
        d_marcas_blancas = {'mercadona':'hacendado','carrefour':'carrefour','consum':'consum',
                            'el corte inglés':'el corte inglés','dia':'dia'}
        if marca in d_marcas_blancas:
            marca_blanca = d_marcas_blancas[marca]
            coincidencia = re.compile(fr'\b{marca_blanca}\b',re.IGNORECASE)
            if coincidencia.search(texto):
                return True
        return False

def read_barcodes(frame):
    barcodes = decode(frame)
    for barcode in barcodes:
        barcode_data = barcode.data.decode('utf-8')
        barcode_type = barcode.type
        x, y, w, h = barcode.rect
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

        # Mostrar información del código de barras
        text = f"{barcode_data} ({barcode_type})"
        print("[INFO] Encontrado {} código: {}".format(barcode_data, barcode_type))
        cv2.putText(frame, text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        if barcode_data is not None:
            return (barcode_data,True)
    return (None,False)

def generar_tabla(lista):
    df = pd.DataFrame('---',columns= lista ,index='nombre_producto precio precio_unitario'.split())
    return df

def realizar_consulta(codigo):
    url = f"https://go-upc.com/search?q={codigo}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text,'html.parser')
            return soup
        else:
            print(f"Error en la solicitud. Código de error: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"Error en la solicitud: {e}")

def camara():
    cap = cv2.VideoCapture(0)
    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error al capturar el cuadro")
            break

        numero,barcode_detected = read_barcodes(frame)
        cv2.imshow('Barcode Scanner', frame)

        if barcode_detected:
            break

        if cv2.waitKey(1) & 0xFF == 27:  # Presiona Esc para salir
            break
    soup = realizar_consulta(numero)
    clase = soup.find('h1', class_='product-name')
    etiqueta_brand = soup.find('td',class_='metadata-label',string=re.compile(r'brand',re.IGNORECASE))
    if etiqueta_brand:
        brand = (etiqueta_brand.find_next_sibling('td')).get_text(strip=True) + ' '
    if clase:
        producto = clase.text
        prefijo = 0
        for c_np, c_b in zip(producto, brand):
            if c_np == c_b:
                prefijo += 1
            else:
                break
        nombre_producto = producto[prefijo:]
    else:
        raise IndexError('No se encuentra el elemento escaneado')
    lista_super = ['mercadona','carrefour','consum','el corte inglés','dia']
    for super in lista_super:
        if descarte_marcas_blancas(producto, super):
            pass
    generar_tabla(lista_super)
    print(f'{brand}: {nombre_producto}')
    cap.release()
    cv2.destroyAllWindows()

def opcion_2():
    print("Has seleccionado la opción 2.")
    # Agrega aquí el código correspondiente a la opción 2

def main():
    print("Bienvenido al buscador de productos")
    print("Por favor, selecciona una opción de busqueda:")
    print("1. Mediante Camara")
    print("2. Mediante Texto")

    opcion = input("Ingresa el número de la opción deseada (1 o 2): ")

    if opcion == '1':
        camara()
    elif opcion == '2':
        opcion_2()
    else:
        print("Opción no válida. Por favor, ingresa 1 o 2.")

if __name__ == "__main__":
    main()
