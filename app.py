# app.py

# Récupération sécurisée du token
try:
    # st.secrets agit comme un dictionnaire Python
    github_token = st.secrets["github"]["token"] 
except KeyError:
    # ... gestion d'erreur si le secret n'est pas trouvé
    # ...