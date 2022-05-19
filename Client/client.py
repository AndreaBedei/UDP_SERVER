import socket
import time
import sys
import os
from os.path import isfile

sys.path.append(os.path.dirname(os.path.dirname(__file__))) # Permette d'accedere alla cartella Modules.
from Modules.response import Response
from Modules.response import BUF_SIZE

class UDPClient:
    # Costruttore.
    def __init__(self, host, port):
        self.host = host    # Indiizzo host.
        self.port = port    # Porta host.
        self.sock = None    # Socket.

    def configure_client(self):
        # Creazione client socket usando protocollo UDP con indirizzamento IPV4.
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print('Socket creato', flush = True)
        
    # Funzione che tenta d'instaurare la connessione tra client e server, restituendo un booleano.
    def connection_setup(self):
        msg = Response.RESPONSE_HELLO + ' Client connected'
        self.sock.sendto(msg.encode('utf-8'), (self.host, self.port))
        resp, server_address = self.sock.recvfrom(BUF_SIZE)
        content = resp.decode()
        print('\n', content, '\n', flush = True)
        if content.startswith(Response.RESPONSE_FAIL):
            return False
        return True
    
    # Funzione che effettua alcuni controlli sul formato della stringa di comando necessari ai comandi get e put.
    def chekGetAndPut(self, l_data, data):
        file_name=None
        if l_data.startswith('put'):
            try:
                file_name = str.split(str(data), ' ', 2)[1]
            except:
                print('Errore nalla scrittura del comando, reinserirlo correttamente', flush = True)
                return False, file_name
            if not isfile('./' + file_name):
                file_data='File non trovato, reinserire comando completo.\r\n'
                print(file_data, flush = True)
                return False, file_name
        if l_data.startswith('get'):
            try:
                file_name = str.split(str(data), ' ', 2)[1]
            except:
                print('Errore nalla scrittura del comando, reinserirlo correttamente', flush = True)
                return (False, file_name)
        return True, file_name
    
    # Semplice funzione che mostra la risposta ricevuta dal server in seguito all'invio del comando. E' utile principalmente in caso di comando exit.
    def showServerResponse(self):
        resp, server_address = self.sock.recvfrom(BUF_SIZE)
        content = resp.decode()
        print('\n', content, '\n', flush = True)  
    
    # Funzione che gestisce il comando list.
    def get_list(self):
        resp, server_address = self.sock.recvfrom(BUF_SIZE)
        content = resp.decode()
        print('\n', content, '\n', flush = True)
    
    # Funzione che gestisce il comando get.
    def get_file(self, data):
        # Controlli preliminari sul nome del file che si vuole ottenere.
        file_name = str.split(str(data), ' ', 2)[1]
        if isfile('./' + file_name):
            print('Esiste già un file con questo nome nella cartella, ma verrà sovrascritto', flush = True)
        resp, server_address = self.sock.recvfrom(BUF_SIZE)
        receiving = False
        if str(resp.decode()).startswith(Response.RESPONSE_FAIL):
            print('File inesistente sul server', flush = True)
            return
        try:       
            # Inizio sequenza di download del file.
            file = open('./' + file_name , 'wb')    # Creazione nuovo file con il nome del file che si vuole scaricare dal server.
            print('File creato nella cartella corrente', flush = True)
            if resp.decode('utf-8').startswith(Response.RESPONSE_OK):
                self.sock.sendto(Response.RESPONSE_OK.encode(), (self.host, self.port))
                print("Inizio ricezione, attendere...")
                receiving = True    # Booleano che indica se il client è pronto a ricevere il contenuto effettivo del file.
            while receiving:
                # Inizio sequenza di download effettivo del contenuto del file.
                resp, server_address = self.sock.recvfrom(BUF_SIZE)
                if resp.decode('utf-8') == Response.RESPONSE_DATA:  # Se il server comunica di aver inviato degli altri dati.
                    # Scrittura dei dati ricevuti dal server in coda al file.
                    self.sock.sendto(Response.RESPONSE_OK.encode(), (self.host, self.port))
                    #print('Invio OK dopo status', flush = True)
                    resp, server_address = self.sock.recvfrom(BUF_SIZE)
                    file.write(resp)
                    #print('Ricezione dati', flush = True)
                    self.sock.sendto(Response.RESPONSE_OK.encode(), (self.host, self.port))
                    #print('Invio OK dopo dati', flush = True)
                elif resp.decode('utf-8') == Response.RESPONSE_DONE:    # Se il server comunica di aver terminato l'invio del suo file.
                    file.close()
                    print('Ricezione conclusa', flush = True)
                    self.sock.sendto(Response.RESPONSE_OK.encode(), (self.host, self.port))
                    receiving = False
                else:   # Qualche errore è accaduto sul server.
                    file.close()
                    receiving = False
        except Exception as info:
            print(info, flush = True)
        finally:
            file.close()
        
    # Funzione che gestisce il comando put.
    def put_file(self, file_name):
        resp, server_address = self.sock.recvfrom(BUF_SIZE)
        r = resp.decode('utf-8')
        if r.startswith(Response.RESPONSE_FAIL):
            print(r + '\n', flush = True)
            return
        print("Inizio invio...", flush = True)
        try:
            # Inizio sequenza di upload.
            file_path = './' + file_name
            file = open(file_path, 'rb')
            
            # Scrittura dell'avanzamento percentuale di upload.
            file_size = os.path.getsize(file_path)
            perc = 0
            tenth = file_size / 10
            threshold = tenth 
            content = file.read(BUF_SIZE)
            while content:
                pos = file.tell()
                if pos >= threshold:
                    perc = perc + 10
                    print(str(perc) + '%', flush = True)
                    threshold = threshold + tenth
                
                # Inizio upload effettivo del file.
                self.sock.sendto(Response.RESPONSE_DATA.encode('utf-8'), (self.host, self.port))    # Invio stato.
                resp, server_address = self.sock.recvfrom(BUF_SIZE)     # Attesa risposta dopo l'invio dello stato.
                if resp.decode('utf-8').startswith(Response.RESPONSE_OK):
                    self.sock.sendto(content, (self.host, self.port))   # Invio dati. 
                    resp, server_address = self.sock.recvfrom(BUF_SIZE)     # Attesa risposta dopo l'invio di dati.
                    if resp.decode('utf-8').startswith(Response.RESPONSE_OK):
                        content = file.read(BUF_SIZE) # Lettura della prossima sezione del file da inviare.
                    else:
                        # Errore del server, bisogna terminare immediatamente l'invio.
                        print("Errore ricevuto. Chiusura file...", flush = True)
                        return         
                else:
                    # Errore nel server: il suo stato attuale non permette l'invio il file.
                    print("Errore ricevuto. Chiusura file...", flush = True)
                    return   
                
            # Terminazione invio file.
            print("Invio stato DONE. Chiusura file...", flush = True)
            self.sock.sendto(Response.RESPONSE_DONE.encode('utf-8'), (self.host, self.port))    # Invio segnale di terminazione del file.
            resp, server_address = self.sock.recvfrom(BUF_SIZE)     # Attesa risposta dopo la terminazione del file.
            if resp.decode('utf-8').startswith(Response.RESPONSE_OK):
                print("Invio completato con successo", flush = True)
            else:
                print("Invio completato con errori", flush = True)
        finally:
            file.close()

    # Funzione che gestisce le richieste del client e le invia al server.
    def interact_with_server(self):
        try:
            # Si prova ad instaurare la connessione tra client e server, bloccando il processo client in caso di errore di instaurazione.
            if not self.connection_setup():
               return
            while True:
                # Inserimento comando da spedire.
                data=input('Inserire comando: ')
                l_data = data.lower()
                t1=time.time()  # Semplice timer a fini puramente statistici.
                [controllo, file_name] = self.chekGetAndPut(l_data, data)
                if not controllo:
                    continue
                self.sock.sendto(str(data).encode('utf-8'), (self.host, self.port)) # Invio del comando al server.
                
                # Identificazione comando.
                if l_data == 'exit' :
                    self.showServerResponse()
                    return
                elif l_data.startswith('list'):
                    self.get_list()
                elif l_data.startswith('get'):
                    self.get_file(data)
                elif l_data.startswith('put'):  
                    self.put_file(file_name)
                else :
                    self.showServerResponse()
                print('Tempo ricezione risposta in secondi: ', (time.time()-t1), flush = True)
        except OSError as err:
            print(err, flush = True)
        except KeyboardInterrupt:
            return
        finally:
            # Chiusura socket.
            self.sock.close()

def main():
    # Si crea il client UDP e si configurano si uoi parametri. Infine, si instaura l'interazione con il server UDP.
    udp_client = UDPClient('127.0.0.1', 10002)
    udp_client.configure_client()
    udp_client.interact_with_server()

if __name__ == '__main__':
    main()