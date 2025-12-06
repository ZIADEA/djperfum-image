import json
from datetime import datetime
from pathlib import Path
import smtplib
from email.mime.text import MIMEText

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

# ================== UTILITAIRE RERUN (compat) ======================

def do_rerun():
    """Compatibilité entre st.rerun (récent) et st.experimental_rerun (ancien)."""
    try:
        st.rerun()
    except AttributeError:
        st.experimental_rerun()

# ================== FONCTIONS UTILES ==================

@st.cache_data
def load_catalog():
    """
    Charge le catalogue CSV et force un ID interne cohérent :

    - image_id = index de la ligne + 1
    - image_path = images/{image_id}.png

    Donc la ligne 1 du CSV = id 1 = images/1.png
         la ligne 2 du CSV = id 2 = images/2.png
         etc.
    """
    try:
        df = pd.read_csv(CATALOG_CSV)
    except Exception:
        return pd.DataFrame()

    # On ignore complètement les colonnes d'ID existantes,
    # on repart sur un index propre.
    df = df.reset_index(drop=True)
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
    st.session_state.setdefault("page", "Accueil")  # page courante pour la nav


def normalize_cart_items(cart_list):
    """
    S'assure que chaque item du panier a un champ 'units' (nombre de flacons).
    Utile pour compatibilité avec d'anciens fichiers users.json.
    """
    normalized = []
    for item in cart_list:
        if "units" not in item:
            item["units"] = 1
        normalized.append(item)
    return normalized


def sync_current_user_to_file():
    """Recopie l’état en mémoire (cart/favs/history) vers users.json pour l’utilisateur courant."""
    user = st.session_state.get("user")
    if not user:
        return
    users = load_users()
    if user not in users:
        users[user] = {"password": st.session_state.get("password_plain") or ""}
    users[user]["password"] = st.session_state.get("password_plain") or ""
    # normalisation du panier avant sauvegarde
    cart = normalize_cart_items(st.session_state.get("cart", []))
    st.session_state["cart"] = cart
    users[user]["cart"] = cart
    users[user]["favorites"] = list(st.session_state.get("favorites", set()))
    users[user]["history"] = st.session_state.get("history", [])
    save_users(users)


def login_user(username: str, password: str) -> bool:
    users = load_users()
    if username in users and users[username].get("password") == password:
        st.session_state["user"] = username
        st.session_state["password_plain"] = password
        data = users[username]
        # normalisation du panier pour intégrer 'units'
        st.session_state["cart"] = normalize_cart_items(data.get("cart", []))
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
    """Affiche un message + bouton Se connecter si l'utilisateur n'est pas logué."""
    if st.session_state.get("user") is None:
        st.warning("Vous devez être connecté pour accéder à cette page.")
        if st.button("Se connecter", key="require_login_btn"):
            st.session_state["page"] = "Login / Signup"
            do_rerun()
        st.stop()


def add_to_cart(name, price, qte_ml, units=1):
    """Ajoute un parfum au panier, avec quantité en ml + nombre de flacons."""
    item = {
        "name": name,
        "price": price,
        "qte_ml": qte_ml,
        "units": int(units) if units else 1,
    }
    st.session_state["cart"].append(item)
    sync_current_user_to_file()


def add_to_favorites(name):
    favs = st.session_state["favorites"]
    favs.add(name)
    st.session_state["favorites"] = favs
    sync_current_user_to_file()


def get_cart_item_count():
    """Retourne le nombre total de flacons dans le panier."""
    cart = st.session_state.get("cart", [])
    return sum(int(item.get("units", 1)) for item in cart)


def render_bot_link(prefix: str):
    """
    Bouton pour aller à la page Chatbot (navigation interne),
    au lieu d'un lien externe.
    """
    if st.button(
        "Discuter avec notre bot (ouvrir le chatbot)",
        key=f"bot_btn_{prefix}",
    ):
        st.session_state["page"] = "Chatbot"
        do_rerun()

def get_parfum_by_name(name: str):
    """
    Retourne la ligne du catalogue (Series) correspondant Çÿ ce parfum,
    ou None si introuvable.
    """
    if df_catalog is None or df_catalog.empty:
        return None

    sub = df_catalog[df_catalog["name"] == name]
    if sub.empty:
        sub = df_catalog[df_catalog["name"].str.lower() == str(name).lower()]

    if sub.empty:
        return None

    return sub.iloc[0]

def get_image_path_for_name(name: str) -> str:
    """
    Retourne le chemin d'image pour un parfum donné, à partir de df_catalog.
    On fait une recherche exacte puis insensible à la casse.
    """
    row = get_parfum_by_name(name)
    if row is None:
        return ""
    return row.get("image_path", "") or ""

def render_product_list(df, key_prefix: str):
    """
    Affiche une liste de produits avec :
    - recherche
    - tri
    - choix ml
    - nombre de flacons
    - boutons panier/favoris
    - lien fiche parfum
    """
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
                if st.button(
                    "Aller à la page Login / Signup",
                    key=f"login_redirect_{key_prefix}_{idx}",
                ):
                    st.session_state["page"] = "Login / Signup"
                    do_rerun()
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

                units = st.number_input(
                    "Nombre de flacons",
                    min_value=1,
                    max_value=20,
                    step=1,
                    value=1,
                    key=f"units_{key_prefix}_{idx}",
                )

                if st.button(
                    "Ajouter au panier",
                    key=f"add_cart_{key_prefix}_{idx}",
                ):
                    add_to_cart(name, price, qty, units)
                    st.success("Ajouté au panier.")

                if st.button(
                    "Ajouter aux favoris",
                    key=f"add_fav_{key_prefix}_{idx}",
                ):
                    add_to_favorites(name)
                    st.success("Ajouté aux favoris.")

        st.markdown("---")


def render_parfum_detail(df_catalog, compo_map, parfum_id: int):
    """Affiche la fiche détaillée d'un parfum à partir de son image_id (avec ajout panier + favoris)."""
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

        st.markdown("---")
        user = st.session_state.get("user")
        if user is not None:
            qty_ml = st.selectbox(
                "Quantité (ml)",
                [10, 20, 30],
                key=f"detail_qty_{parfum_id}",
            )
            if qty_ml == 10:
                price = price10
            elif qty_ml == 20:
                price = price20
            else:
                price = price30

            units = st.number_input(
                "Nombre de flacons",
                min_value=1,
                max_value=20,
                step=1,
                value=1,
                key=f"detail_units_{parfum_id}",
            )

            if st.button("Ajouter au panier", key=f"detail_add_cart_{parfum_id}"):
                add_to_cart(name, price, qty_ml, units)
                st.success("Ajouté au panier.")

            if st.button("Ajouter aux favoris", key=f"detail_add_fav_{parfum_id}"):
                add_to_favorites(name)
                st.success("Ajouté aux favoris.")
        else:
            pass


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


def send_contact_email(nom, email, objet, message):
    """
    Envoie un email à djeryala@gmail.com en utilisant st.secrets.

    secrets.toml (exemple) :
    [email]
    host = "smtp.gmail.com"
    port = 587
    username = "ton_adresse_gmail"
    password = "mot_de_passe_ou_app_password"
    """
    try:
        host = st.secrets["email"]["host"]
        port = int(st.secrets["email"]["port"])
        username = st.secrets["email"]["username"]
        password = st.secrets["email"]["password"]
    except Exception:
        raise RuntimeError(
            "Configuration email manquante dans st.secrets['email']."
        )

    to_email = "djeryala@gmail.com"

    body = f"""Nouveau message via DJERIPERFUM

Nom : {nom}
Email : {email}
Objet : {objet}

Message :
{message}
"""

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = objet if objet else "Nouveau message via DJERIPERFUM"
    msg["From"] = username
    msg["To"] = to_email

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(username, password)
        server.send_message(msg)


# ================== DONNÉES & ÉTAT ==========================

df_catalog = load_catalog()
compo_map = load_compositions()
ensure_session_state()


# ========== ROUTE DÉTAILLÉE VIA QUERY PARAM POUR PARFUM =========

params = st.query_params

# Sur les versions récentes de Streamlit, params["parfum_id"] est une **chaîne**,
# pas une liste, donc on NE met plus [0].
parfum_id_param = params.get("parfum_id", None)

if parfum_id_param is not None:
    try:
        pid = int(parfum_id_param)
        render_parfum_detail(df_catalog, compo_map, pid)
        st.stop()
    except ValueError:
        # si l'id n'est pas un entier, on continue normalement
        pass

# ========== NAVIGATION PAR RADIO + SESSION_STATE ==========

PAGES = [
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
]

# S'assurer que la page stockée est valide
if st.session_state["page"] not in PAGES:
    st.session_state["page"] = "Accueil"

st.sidebar.title("DJERIPERFUM")

user = st.session_state.get("user")
if user:
    st.sidebar.write(f"Connecté : **{user}**")
else:
    st.sidebar.write("Non connecté")

# Badge nombre d'articles dans le panier
cart_count = get_cart_item_count()
st.sidebar.markdown(f"**Panier : {cart_count} article(s)**")

page_radio = st.sidebar.radio(
    "Navigation",
    PAGES,
    index=PAGES.index(st.session_state["page"]),
    key="nav_radio",
)

# Si l'utilisateur change de page via le menu, on met à jour la page et on relance
if page_radio != st.session_state["page"]:
    st.session_state["page"] = page_radio
    do_rerun()

page = st.session_state["page"]

st.sidebar.markdown("---")
st.sidebar.caption("Projet Botpress + Streamlit — DJERIPERFUM")

# ================== PAGES ============================

if page == "Accueil":
    st.title("DJERIPERFUM – Boutique de décants + conseiller virtuel")

    st.markdown(
        """
    ### Concept

    DJERIPERFUM est une mini-boutique de parfums de 10/20/30 ml avec un
    assistant virtuel intelligent développé avec Botpress.
    L'objectif est de permettre aux clients de découvrir et acheter des
    parfums, tout en bénéficiant de recommandations personnalisées.
    """
    )

elif page == "Parfums homme":
    st.title("Parfums Homme")
    render_bot_link("homme")

    if df_catalog.empty:
        st.warning("Catalogue vide ou fichier CSV manquant.")
    else:
        df = df_catalog[df_catalog["category"].str.contains("Homme", na=False)]
        st.write(f"{len(df)} références trouvées dans cette catégorie.")
        render_product_list(df, "homme")

elif page == "Parfums femme":
    st.title("Parfums Femme")
    render_bot_link("femme")

    if df_catalog.empty:
        st.warning("Catalogue vide ou fichier CSV manquant.")
    else:
        df = df_catalog[df_catalog["category"].str.contains("Femme", na=False)]
        st.write(f"{len(df)} références trouvées dans cette catégorie.")
        render_product_list(df, "femme")

elif page == "Parfums mixte / niche":
    st.title("Parfums Mixte / Niche")
    render_bot_link("mixte")

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
    cart = normalize_cart_items(cart)
    st.session_state["cart"] = cart

    if not cart:
        st.info("Votre panier est vide.")
    else:
        # Bouton pour vider tout le panier
        if st.button("Vider tout le panier"):
            st.session_state["cart"] = []
            sync_current_user_to_file()
            st.success("Panier vidé.")
        else:
            st.markdown("### Détail des articles")

            total = 0.0
            indices_to_delete = []
            changed = False

            for i, item in enumerate(cart):
                name = item["name"]
                price = float(item["price"])
                qte = item["qte_ml"]
                units = int(item.get("units", 1))
                parfum_row = get_parfum_by_name(name)
                image_path = ""
                image_id = None
                if parfum_row is not None:
                    image_path = parfum_row.get("image_path", "") or ""
                    image_id = (
                        int(parfum_row.get("image_id"))
                        if "image_id" in parfum_row
                        else None
                    )

                # 5 colonnes : image | détails | qté flacons | prix | suppression
                cols = st.columns([1, 3, 2, 2, 2])

                with cols[0]:
                    if image_path:
                        try:
                            st.image(image_path, width=70)
                        except Exception:
                            pass

                with cols[1]:
                    if image_id is not None:
                        st.markdown(f"[**{name}**](?parfum_id={image_id})")
                    else:
                        st.write(f"**{name}**")
                    st.write(f"{qte} ml")

                with cols[2]:
                    new_units = st.number_input(
                        "Nombre de flacons",
                        min_value=1,
                        max_value=50,
                        step=1,
                        value=units,
                        key=f"cart_units_{i}",
                    )
                    if new_units != units:
                        cart[i]["units"] = int(new_units)
                        changed = True

                with cols[3]:
                    line_total = price * cart[i]["units"]
                    st.write(f"Prix unitaire : {price:.0f} DH")
                    st.write(f"Total ligne : {line_total:.0f} DH")
                    total += line_total

                with cols[4]:
                    if st.button("Supprimer", key=f"del_{i}"):
                        indices_to_delete.append(i)

            # Suppression des lignes demandées
            if indices_to_delete:
                for idx in sorted(indices_to_delete, reverse=True):
                    cart.pop(idx)
                changed = True

            st.session_state["cart"] = cart

            if changed:
                sync_current_user_to_file()

            st.markdown("---")
            st.write(f"**Total : {total:.0f} DH**")

            if st.button("Valider l'achat"):
                st.session_state["history"].append(
                    {
                        "items": cart.copy(),
                        "total": total,
                        "timestamp": datetime.now().isoformat(),
                    }
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
            ts = order.get("timestamp")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts)
                    st.caption(dt.strftime("Date et heure : %d/%m/%Y %H:%M"))
                except Exception:
                    st.caption(f"Date et heure : {ts}")
            for item in order["items"]:
                units = int(item.get("units", 1))
                name = item["name"]
                qte = item["qte_ml"]
                price = float(item["price"])
                parfum_row = get_parfum_by_name(name)
                image_path = ""
                image_id = None
                if parfum_row is not None:
                    image_path = parfum_row.get("image_path", "") or ""
                    image_id = (
                        int(parfum_row.get("image_id"))
                        if "image_id" in parfum_row
                        else None
                    )

                cols = st.columns([1, 4])

                with cols[0]:
                    if image_path:
                        try:
                            st.image(image_path, width=60)
                        except Exception:
                            pass

                with cols[1]:
                    if image_id is not None:
                        st.markdown(
                            f"[**{name}**](?parfum_id={image_id})"
                            f" — {qte} ml — {units} flacon(s) — {price:.0f} DH / flacon"
                        )
                    else:
                        st.write(
                            f"- **{name}** — {qte} ml — {units} flacon(s) — {price:.0f} DH / flacon"
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
            parfum_row = get_parfum_by_name(name)
            image_path = ""
            image_id = None
            if parfum_row is not None:
                image_path = parfum_row.get("image_path", "") or ""
                image_id = (
                    int(parfum_row.get("image_id"))
                    if "image_id" in parfum_row
                    else None
                )

            cols = st.columns([1, 4])

            with cols[0]:
                if image_path:
                    try:
                        st.image(image_path, width=60)
                    except Exception:
                        pass

            with cols[1]:
                if image_id is not None:
                    st.markdown(f"[**{name}**](?parfum_id={image_id})")
                else:
                    st.write(f"- **{name}**")


elif page == "Me contacter":
    st.title("Contact DJERIPERFUM")

    st.markdown(
        """
    Informations de contact  
    Pour toute question ou demande, vous pouvez utiliser le formulaire ci-dessous
    ou les coordonnées directes.
    """
    )

    st.write("Email direct : contact@djperfum.ma")
    st.write("Téléphone : +212 6 25 50 88 21")
    st.write("Réseau social : https://www.instagram.com/______burna_girl_____/")

    st.markdown("---")
    st.subheader("Formulaire de contact")

    with st.form("contact_form"):
        nom = st.text_input("Votre nom")
        email = st.text_input("Votre email")
        objet = st.text_input("Objet")
        message = st.text_area("Votre message")

        submitted = st.form_submit_button("Envoyer")

        if submitted:
            if not nom or not email or not message:
                st.error("Merci de remplir au minimum votre nom, email et message.")
            else:
                try:
                    send_contact_email(nom, email, objet, message)
                    st.success(
                        "Message envoyé avec succès. Nous vous répondrons dès que possible."
                    )
                except Exception as e:
                    st.error(
                        "Une erreur est survenue lors de l'envoi du message. "
                        "Vérifiez la configuration de l'email dans secrets.toml."
                    )
                    # Pour debug éventuel en local :
                    st.write(str(e))

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
