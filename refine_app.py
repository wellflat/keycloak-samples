#!/usr/bin/env python

import os
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from jose import JWTError
from keycloak import KeycloakOpenID
from keycloak.exceptions import KeycloakInvalidTokenError
from pydantic import BaseModel
from dotenv_flow import dotenv_flow
from pprint import pprint

dotenv_flow("dev")

# --- Keycloak設定 ---
KEYCLOAK_SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL", "test")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "test")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "test")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "YOUR_CLIENT_SECRET")


# --- OAuth2スキーム ---
# 認可コードフローを使用します
# ユーザーはauthorizationUrlにリダイレクトされ、認証後にtokenUrlでトークンが交換されます
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/auth",
    tokenUrl=f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token",
)

# --- FastAPIインスタンス ---
app = FastAPI(
    title="WebAPI with OpenID Connect (Authorization Code Flow)",
    description="A simple example of FastAPI integration with Keycloak for authentication and authorization.",
    version="1.0.0",
    swagger_ui_oauth2_redirect_url="/docs/oauth2-redirect",
    # Swagger UIがトークンを取得する際に使用するOAuth2クライアント情報を設定します
    # これにより、confidentialクライアントの認証が可能になります
    swagger_ui_init_oauth={
        "clientId": KEYCLOAK_CLIENT_ID,
        "clientSecret": KEYCLOAK_CLIENT_SECRET,
        "usePkceWithAuthorizationCodeGrant": True,  # セキュリティ向上のためPKCEを有効化
    },
)

# --- Keycloak OpenID Connectクライアント ---
# Keycloakとの通信を管理します
keycloak_openid = KeycloakOpenID(
    server_url=KEYCLOAK_SERVER_URL,
    client_id=KEYCLOAK_CLIENT_ID,
    realm_name=KEYCLOAK_REALM,
    client_secret_key=KEYCLOAK_CLIENT_SECRET,
)


# --- JWTペイロードのモデル ---
class User(BaseModel):
    username: str
    email: str | None = None
    roles: list[str] = []

# --- 依存性: 現在のユーザーを取得 ---
async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    JWTトークンをデコード・検証し、ユーザー情報を返します。
    python-keycloakライブラリの機能を利用して、トークン検証ロジックを抽象化しています。
    無効なトークンの場合はHTTPExceptionを送出します
    """
    try:
        # Keycloakライブラリの機能を使ってトークンをデコード・検証します。
        # 公開鍵の取得、署名検証、有効期限検証などはライブラリが内部で処理します。
        payload = keycloak_openid.decode_token(
            token
            # audience引数は、内部で使用しているライブラリ(jwcrypto)が直接サポートしていないため
            # TypeErrorを引き起こします。検証はデコード後に手動で行います。
        )
        pprint(payload)

        # audience(aud)クレームを手動で検証します。
        # audクレームは文字列、または文字列の配列の場合があります。
        audience = payload.get("aud")
        is_audience_valid = False
        if isinstance(audience, str):
            is_audience_valid = (audience == KEYCLOAK_CLIENT_ID)
        elif isinstance(audience, list):
            is_audience_valid = (KEYCLOAK_CLIENT_ID in audience)

        if not is_audience_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid audience",
                headers={"WWW-Authenticate": "Bearer"},
            )
        # ペイロードからユーザー情報を抽出
        username: str | None = payload.get("preferred_username")
        email: str | None = payload.get("email")
        
        # クライアントロール情報を抽出
        resource_access = payload.get("resource_access", {})
        client_roles = resource_access.get(KEYCLOAK_CLIENT_ID, {}).get("roles", [])

        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials: username missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return User(username=username, email=email, roles=client_roles)

    # python-keycloakはトークンが無効な場合にKeycloakInvalidTokenErrorや
    # jwcryptoライブラリ由来の例外(署名エラー、期限切れなど)を送出します。
    except (KeycloakInvalidTokenError, JWTError, Exception) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

# --- 依存性: 特定のロールを要求 ---
def require_role(required_role: str):
    """
    特定のロールを持つユーザーのみアクセスを許可する依存関係を生成するファクトリ
    """
    async def role_checker(current_user: User = Depends(get_current_user)):
        if required_role not in current_user.roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have the required '{required_role}' role",
            )
        return current_user
    return role_checker


# --- APIエンドポイント ---
@app.get("/")
async def root():
    """
    誰でもアクセスできる公開エンドポイント
    """
    return {"message": "Hello, this is a public endpoint!"}

@app.get("/protected", response_model=User)
async def protected_route(current_user: User = Depends(get_current_user)):
    """
    認証されたユーザーのみがアクセスできる保護されたエンドポイント
    """
    return current_user

@app.get("/protected/role-required", response_model=User)
async def protected_role_route(
    # 'user'ロールを持つユーザーのみアクセス可能
    current_user: User = Depends(require_role("user"))
):
    """
    認証され、かつ特定のロール('user')を持つ認可されたユーザーのみがアクセスできるエンドポイント
    """
    return current_user

@app.get("/callback")
async def callback():
    return {"message": "Callback endpoint"}


if __name__ == "__main__":
    import uvicorn
    if KEYCLOAK_CLIENT_SECRET == "YOUR_CLIENT_SECRET":
        print("\n[警告] KEYCLOAK_CLIENT_SECRETが設定されていません")
    uvicorn.run(app, host="0.0.0.0", port=8000)