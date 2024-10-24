from enum import IntEnum,StrEnum,Enum, auto

#ßee https://www.youtube.com/watch?v=AMTZG5W3rKQ con Py3.11 

def main():
    #IntEnum
    print("Esempi con IntEnum")
    class HttpStatus(IntEnum):  #IntEnum
        OK = 200
        NOT_FOUND = 404
        ERROR = 500
        BAD_GATEWAY = 502

    status: HttpStatus = HttpStatus.OK
    print(status) #se fosse stato Enum sarebbe OK mentre con IntEnum ritorna 200
    print(status.value)

    #possibile operation on IntEnum
    if status==200:
        print("Staus is ok")
    if status>0:
        print("Staus is valid")
    print(status+100)
    print([sta for sta in HttpStatus])

    #
    print("Esempi con StrEnum disponibile con Py 3.11")
    class Role(StrEnum):
        ADMIN='admin'
        EDITOR='editor'
        VIEWER='viewer'
    role:Role = Role.ADMIN
    print(role)
    print(role.value)
    print(role.upper() ) #role è considerata una stringa e si possono usare i metodi se usato StrEnum
    if role=='admin':
        print("user is admin")
    if role==Role.ADMIN: #better
        print("user is admin with better")
    match role:
        case Role.ADMIN:
            print("user is admin with match")
    print(f'User with capitalize: {role.capitalize()}')

    print("Esempi con StrEnum e auto disponibile con Py 3.11")
    class RoleWithAuto(StrEnum):
        ADMIN=auto()    #AUTO mette il valore stringa minuscola
        EDITOR=auto()
        VIEWER=auto()
    roleW:RoleWithAuto = RoleWithAuto.ADMIN
    print(roleW)
    print([role for role in RoleWithAuto])



if __name__ == "__main__":
    main()
