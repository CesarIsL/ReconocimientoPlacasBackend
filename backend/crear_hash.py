import bcrypt
import sys

# La sal (salt) es un valor aleatorio que asegura que dos contraseñas iguales tengan hashes diferentes
def generar_hash(password):
    # Genera la sal y hashea la contraseña
    # bcrypt.gensalt() se asegura de usar una sal nueva cada vez.
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Error: Debes pasar una contraseña como argumento.")
        print("Ejemplo: python crear_hash.py mi_password_secreta")
        sys.exit(1)

    password_a_hashear = sys.argv[1]
    
    hash_generado = generar_hash(password_a_hashear)
    
    print("\n----------------------------------------------------------------------")
    print(f"Contraseña Original: {password_a_hashear}")
    print("----------------------------------------------------------------------")
    print("¡COPIA ESTE HASH COMPLETO y pégalo en tu tabla 'empleados' de PostgreSQL!")
    print(f"HASH GENERADO: {hash_generado}")
    print("----------------------------------------------------------------------\n")