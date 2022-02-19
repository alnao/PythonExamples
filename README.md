# PythonExamples
Python Examples

## FromOthersSite
- Coffe.py

  from https://github.com/uxai/100daysofcode/blob/main/Day%2015/coffee_machine.py

  to run
  ```
  $ python3 FromOthersSite/Coffe.py 
  ```


## Simple

### conto1.py
- esercitazione classe ContoCorrente 
	
    inizializzatore con 3 parametri (nome titolare, numero conto e saldo) 
	
    tre attributi (nome, conto e saldo)
	
    metodo preleva con un parametro importo
	
    metodo deposita con un parametro importo
	
    metodo descrizione senza paraemtri e visualizza : nome, conto e saldo
	
    crea folder, crea conto1.py
	
    codice per testare la classe: 2 conti

- to run 
  ```
  $ python3 Simple/conto1.py 
  ```

### conto2.py
- esercitazione classe ContoCorrente 
	
    prendere spunto dal conto1.py ma nascondere il saldo come proprietà semplice
    
    una property ''privata'' , modificando il saldo in __saldo
    
    nascondere attributo saldo, getter e setter

- to run 
  ```
  $ python3 Simple/conto2.py 
  ```


### conto3.py
- esercitazione classe Conto come padre di ContoCorrente
	
    in conto ci devono essere nome e numero conto
    
- to run 
  ```
  $ python3 Simple/conto3.py 
  ```

### conto4.py
- esercitazione classe Gestore Conto corrente

    crea metodo bonifico per prelevare da un conto e fare un deposito ad un altro

- to run 
  ```
  $ python3 Simple/conto4.py 
  ```