import json
from pathlib import Path

import pandas as pd
import streamlit as st

# ================== CONFIG GLOBALE ==================

st.set_page_config(
    page_title="DJERIPERFUM - Boutique décants + chatbot",
    layout="wide",
)

# ================== CONSTANTES ======================

CATALOG_CSV = "Catalogue_Parfums_Complet.csv"   # ton CSV actuel
USERS_FILE = "users.json"
COMPO_FILE = "parfums_composition.txt"          # nouveau fichier texte

# Lien shareable Botpress
CHATBOT_URL = (
    "https://cdn.botpress.cloud/webchat/v3.3/shareable.html"
    "?configUrl=https://files.bpcontent.cloud/2025/10/06/14/20251006143331-TLGNO0TS.json"
)

# ================== FONCTIONS UTILES ==================

@st.cache_data
def load_catalog():
    """Charge le catalogue CSV et ajoute la colonne image_path."""
    try:
        df = pd.read_csv(CATALOG_CSV)
    except Exception:
        return pd.DataFrame()

    df = df.reset_index(drop=True)

    # si une colonne image_id existe déjà on l’utilise, sinon index + 1
    if "image_id" in df.columns:
        df["image_id"] = df["image_id"].astype(int)
    else:
        df["image_id"] = df.index + 1

    df["image_path"] = df["image_id"].apply(lambda i: f"images/{i}.png")
    return df


@st.cache_data
def load_compositions():
    """
    Lit parfums_composition.txt avec des sections de type:

    ### NOM DU PARFUM
    Famille olfactive : ...
    Notes de tête : ...
    Notes de cœur : ...
    Notes de fond : ...

    et retourne un dict {nom: texte_markdown}
    """
    path = Path(COMPO_FILE)
    if not path.exists():
        return {}

    compositions = {}
    current_name = None
    buffer = []

    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if line.startswith("### "):
                # on ferme l’ancien bloc
                if current_name is not None:
                    compositions[current_name] = "\n".join(buffer).strip()
                current_name = line[4:].strip()
                buffer = []
            else:
                buffer.append(line)

    # dernier bloc
    if current_name is not None:
        compositions[current_name] = "\n".join(buffer).strip()

    return compositions


compositions = load_compositions()



def load_users():
    """Charge le fichier users.json (ou dict vide)."""
    path = Path(USERS_FILE)
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_users(users: dict):
    """Sauvegarde le dictionnaire d’utilisateurs dans users.json."""
    path = Path(USERS_FILE)
    with path.open("w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def ensure_session_state():
    st.session_state.setdefault("user", None)
    st.session_state.setdefault("password_plain", None)
    st.session_state.setdefault("cart", [])
    st.session_state.setdefault("favorites", set())
    st.session_state.setdefault("history", [])


def sync_current_user_to_file():
    """Recopie l’état en mémoire (cart/favs/history) vers users.json pour l’utilisateur courant."""
    user = st.session_state.get("user")
    if not user:
        return
    users = load_users()
    if user not in users:
        users[user] = {"password": st.session_state.get("password_plain") or ""}
    users[user]["password"] = st.session_state.get("password_plain") or ""
    users[user]["cart"] = st.session_state.get("cart", [])
    users[user]["favorites"] = list(st.session_state.get("favorites", set()))
    users[user]["history"] = st.session_state.get("history", [])
    save_users(users)


def login_user(username: str, password: str) -> bool:
    users = load_users()
    if username in users and users[username].get("password") == password:
        st.session_state["user"] = username
        st.session_state["password_plain"] = password
        data = users[username]
        st.session_state["cart"] = data.get("cart", [])
        st.session_state["favorites"] = set(data.get("favorites", []))
        st.session_state["history"] = data.get("history", [])
        return True
    return False


def signup_user(username: str, password: str):
    users = load_users()
    if username in users:
        return False, "Ce nom d'utilisateur existe déjà."
    users[username] = {
        "password": password,
        "cart": [],
        "favorites": [],
        "history": [],
    }
    save_users(users)
    st.session_state["user"] = username
    st.session_state["password_plain"] = password
    st.session_state["cart"] = []
    st.session_state["favorites"] = set()
    st.session_state["history"] = []
    return True, "Compte créé."


def require_login():
    if st.session_state.get("user") is None:
        st.warning("Vous devez être connecté pour accéder à cette page.")
        st.stop()


def add_to_cart(name, price, qte_ml):
    st.session_state["cart"].append(
        {"name": name, "price": price, "qte_ml": qte_ml}
    )
    sync_current_user_to_file()


def add_to_favorites(name):
    favs = st.session_state["favorites"]
    favs.add(name)
    st.session_state["favorites"] = favs
    sync_current_user_to_file()


def render_bot_link():
    """Lien en haut des pages catalogue pour ouvrir le chatbot."""
    st.markdown(
        f"[Discuter avec notre bot (ouvrir le chatbot)]({CHATBOT_URL})",
        help="Ouvre l'interface Botpress dans un nouvel onglet.",
    )


def render_product_list(df, key_prefix: str):
    """Affiche une liste de produits avec recherche, tri, quantités, boutons panier/favoris + lien fiche parfum."""
    if df.empty:
        st.info("Aucun parfum dans cette catégorie.")
        return

    col_search, col_sort = st.columns([2, 1])

    with col_search:
        search = st.text_input(
            "Rechercher un parfum par nom",
            key=f"search_{key_prefix}",
            placeholder="Ex : Sauvage, Good Girl, Baccarat...",
        )

    with col_sort:
        sort = st.selectbox(
            "Trier par",
            ["Nom A-Z", "Prix 10 ml croissant", "Prix 10 ml décroissant"],
            key=f"sort_{key_prefix}",
        )

    if search:
        df = df[df["name"].str.contains(search, case=False, na=False)]

    if sort == "Prix 10 ml croissant":
        df = df.sort_values("price10", ascending=True)
    elif sort == "Prix 10 ml décroissant":
        df = df.sort_values("price10", ascending=False)
    else:
        df = df.sort_values("name", ascending=True)

    if df.empty:
        st.info("Aucun parfum ne correspond à la recherche.")
        return

    user = st.session_state.get("user")

    for idx, (_, row) in enumerate(df.iterrows()):
        name = str(row.get("name", ""))
        price10 = float(row.get("price10", 0) or 0)
        price20 = float(row.get("price20", 0) or 0)
        price30 = float(row.get("price30", 0) or 0)
        image_id = int(row.get("image_id", 0))

        col1, col2, col3 = st.columns([1, 2, 1])

        with col1:
            img_path = row.get("image_path", "")
            try:
                if img_path:
                    st.image(img_path, use_container_width=True)
            except Exception:
                pass

        with col2:
            st.subheader(name)
            st.write(f"Prix 10 ml : {price10:.0f} DH")
            st.write(f"Prix 20 ml : {price20:.0f} DH")
            st.write(f"Prix 30 ml : {price30:.0f} DH")

            # Lien vers la fiche détail avec query param
            st.markdown(
                f"[Voir la fiche détaillée](?parfum_id={image_id})",
                help="Ouvrir la fiche de ce parfum (image, prix, composition).",
            )

        with col3:
            if user is None:
                st.caption("Connectez-vous pour ajouter au panier ou aux favoris.")
            else:
                qty = st.selectbox(
                    "Quantité (ml)",
                    [10, 20, 30],
                    key=f"qty_{key_prefix}_{idx}",
                )

                if qty == 10:
                    price = price10
                elif qty == 20:
                    price = price20
                else:
                    price = price30

                if st.button(
                    "Ajouter au panier",
                    key=f"add_cart_{key_prefix}_{idx}",
                ):
                    add_to_cart(name, price, qty)
                    st.success("Ajouté au panier.")

                if st.button(
                    "Ajouter aux favoris",
                    key=f"add_fav_{key_prefix}_{idx}",
                ):
                    add_to_favorites(name)
                    st.success("Ajouté aux favoris.")

        st.markdown("---")


def render_parfum_detail(df_catalog, compo_map, parfum_id: int):
    """Affiche la fiche détaillée d'un parfum à partir de son image_id."""
    if df_catalog.empty:
        st.error("Catalogue vide ou introuvable.")
        return

    sub = df_catalog[df_catalog["image_id"] == parfum_id]
    if sub.empty:
        st.error(f"Parfum introuvable pour l'id {parfum_id}.")
        return

    row = sub.iloc[0]
    name = str(row.get("name", "Parfum"))
    img_path = row.get("image_path", "")
    price10 = float(row.get("price10", 0) or 0)
    price20 = float(row.get("price20", 0) or 0)
    price30 = float(row.get("price30", 0) or 0)

    st.title(name)

    col_img, col_info = st.columns([1, 1])

    with col_img:
        if img_path:
            try:
                st.image(img_path, use_container_width=False, width=350)
            except Exception:
                st.write("Image non disponible.")
        else:
            st.write("Image non disponible.")

    with col_info:
        st.subheader("Prix décants")
        st.write(f"- 10 ml : **{price10:.0f} DH**")
        st.write(f"- 20 ml : **{price20:.0f} DH**")
        st.write(f"- 30 ml : **{price30:.0f} DH**")

    # Composition
    comp = compo_map.get(name.upper())
    st.markdown("---")
    if comp:
        st.subheader("Composition olfactive")
        st.markdown(comp)
    else:
        st.info(
            "La composition de ce parfum n'est pas renseignée dans la base de connaissances."
        )

    st.markdown("---")
    st.markdown(
        "Utilisez le menu de gauche pour revenir au catalogue ou modifiez l'URL pour changer de parfum."
    )


# ================== DONNÉES & ÉTAT ==========================

df_catalog = load_catalog()
compo_map = load_compositions()
ensure_session_state()

# ========== ROUTE DÉTAILLÉE VIA QUERY PARAM =========

params = st.query_params
parfum_id_param = params.get("parfum_id", [None])[0]

if parfum_id_param is not None:
    # Page "fiche parfum" spéciale
    try:
        pid = int(parfum_id_param)
        render_parfum_detail(df_catalog, compo_map, pid)
        st.stop()
    except ValueError:
        # si l'id n'est pas un entier, on continue normalement
        pass

# ================== NAVIGATION =======================

st.sidebar.title("DJERIPERFUM")

user = st.session_state.get("user")
if user:
    st.sidebar.write(f"Connecté : **{user}**")
else:
    st.sidebar.write("Non connecté")

page = st.sidebar.radio(
    "Navigation",
    [
        "Accueil",
        "Parfums homme",
        "Parfums femme",
        "Parfums mixte / niche",
        "Chatbot",
        "Panier",
        "Historique d'achat",
        "Favoris",
        "Me contacter",
        "Login / Signup",
    ],
)

st.sidebar.markdown("---")
st.sidebar.caption("Projet Botpress + Streamlit — DJERIPERFUM")

# ================== PAGES ============================

if page == "Accueil":
    st.title("DJERIPERFUM – Boutique de décants + conseiller virtuel")

    st.markdown(
        """
    ### Concept

    DJERIPERFUM est une mini-boutique de parfums de 10/20/30 ml avec un
    assistant virtuel intelligent développé avec Botpress .
    L'objectif est de permettre aux clients de découvrir et acheter des
    parfums , tout en bénéficiant de recommandations personnalisées .

    """
    )


elif page == "Parfums homme":
    st.title("Parfums Homme")
    render_bot_link()

    if df_catalog.empty:
        st.warning("Catalogue vide ou fichier CSV manquant.")
    else:
        df = df_catalog[df_catalog["category"].str.contains("Homme", na=False)]
        st.write(f"{len(df)} références trouvées dans cette catégorie.")
        render_product_list(df, "homme")

elif page == "Parfums femme":
    st.title("Parfums Femme")
    render_bot_link()

    if df_catalog.empty:
        st.warning("Catalogue vide ou fichier CSV manquant.")
    else:
        df = df_catalog[df_catalog["category"].str.contains("Femme", na=False)]
        st.write(f"{len(df)} références trouvées dans cette catégorie.")
        render_product_list(df, "femme")

elif page == "Parfums mixte / niche":
    st.title("Parfums Mixte / Niche")
    render_bot_link()

    if df_catalog.empty:
        st.warning("Catalogue vide ou fichier CSV manquant.")
    else:
        df = df_catalog[
            df_catalog["category"].str.contains("Niche", na=False)
            | df_catalog["category"].str.contains("Mixte", na=False)
        ]
        st.write(f"{len(df)} références trouvées dans cette catégorie.")
        render_product_list(df, "mixte")

elif page == "Chatbot":
    st.title("Assistant DJERIPERFUM (Botpress)")

    st.markdown(
        """
    Ci-dessous, vous pouvez discuter directement avec le chatbot développé sous Botpress.
    """
    )

    st.components.v1.iframe(CHATBOT_URL, height=600, scrolling=True)

elif page == "Panier":
    st.title("Votre panier")
    require_login()

    cart = st.session_state["cart"]
    if not cart:
        st.info("Votre panier est vide.")
    else:
        total = 0
        for item in cart:
            name = item["name"]
            price = item["price"]
            qte = item["qte_ml"]
            st.write(f"- {name} — {qte} ml — {price:.0f} DH")
            total += price

        st.write(f"**Total : {total:.0f} DH**")

        if st.button("Valider l'achat"):
            st.session_state["history"].append(
                {"items": cart.copy(), "total": total}
            )
            st.session_state["cart"] = []
            sync_current_user_to_file()
            st.success("Achat validé et ajouté à l'historique.")

elif page == "Historique d'achat":
    st.title("Historique d'achat")
    require_login()

    history = st.session_state["history"]
    if not history:
        st.info("Aucun achat pour le moment.")
    else:
        for i, order in enumerate(history, start=1):
            st.subheader(f"Achat {i}")
            for item in order["items"]:
                st.write(
                    f"- {item['name']} — {item['qte_ml']} ml — {item['price']:.0f} DH"
                )
            st.write(f"Total : {order['total']:.0f} DH")
            st.markdown("---")

elif page == "Favoris":
    st.title("Vos parfums favoris")
    require_login()

    favs = st.session_state["favorites"]
    if not favs:
        st.info("Aucun parfum en favori.")
    else:
        for name in sorted(favs):
            st.write(f"- {name}")

elif page == "Me contacter":
    st.title("Contact DJERIPERFUM")

    st.markdown(
        """
    Informations de contact (fictives pour la démonstration) :
    """
    )

    st.write("Email : contact@djperfum.ma")
    st.write("Téléphone : +212 6 25 50 88 21")

elif page == "Login / Signup":
    st.title("Login / Signup")

    tab1, tab2 = st.tabs(["Login", "Signup"])

    with tab1:
        st.subheader("Login")
        username = st.text_input("Nom d'utilisateur", key="login_user")
        password = st.text_input("Mot de passe", type="password", key="login_pass")
        if st.button("Se connecter"):
            if login_user(username, password):
                st.success("Connexion réussie.")
            else:
                st.error("Identifiants incorrects.")

    with tab2:
        st.subheader("Signup")
        new_user = st.text_input("Nouveau nom d'utilisateur", key="signup_user")
        new_pass = st.text_input(
            "Nouveau mot de passe", type="password", key="signup_pass"
        )
        if st.button("Créer le compte"):
            if not new_user or not new_pass:
                st.error("Veuillez saisir un nom d'utilisateur et un mot de passe.")
            else:
                ok, msg = signup_user(new_user, new_pass)
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    if st.session_state.get("user"):
        if st.button("Se déconnecter"):
            sync_current_user_to_file()
            st.session_state["user"] = None
            st.session_state["password_plain"] = None
            st.session_state["cart"] = []
            st.session_state["favorites"] = set()
            st.session_state["history"] = []
            st.success("Déconnecté.")
