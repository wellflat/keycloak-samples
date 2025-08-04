#!/usr/bin/env python

import os
import requests
import json
from dotenv_flow import dotenv_flow

dotenv_flow("dev")


# --- 設定 ---
KEYCLOAK_SERVER_URL = os.getenv("KEYCLOAK_SERVER_URL", "test")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "test")
KEYCLOAK_CLIENT_ID = os.getenv("KEYCLOAK_CLIENT_ID", "test")
KEYCLOAK_CLIENT_SECRET = os.getenv("KEYCLOAK_CLIENT_SECRET", "test")
REDIRECT_URI = "http://trigkey:8000/callback" # Keycloakクライアントに登録したリダイレクトURI

# --- FastAPIアプリケーションのURL ---
API_BASE_URL = "http://trigkey:8000"

def get_tokens_from_code(authorization_code: str) -> dict | None:
    """
    認可コードを使用してKeycloakからアクセストークンとリフレッシュトークンを取得します。
    """
    token_url = f"{KEYCLOAK_SERVER_URL.rstrip('/')}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/token"

    payload = {
        "grant_type": "authorization_code",
        "client_id": KEYCLOAK_CLIENT_ID,
        "client_secret": KEYCLOAK_CLIENT_SECRET,
        "code": authorization_code,
        "redirect_uri": REDIRECT_URI,
    }

    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        print("\n認可コードを使ってKeycloakからトークンを取得中...")
        response = requests.post(token_url, data=payload, headers=headers)
        response.raise_for_status()  # 4xx or 5xx のステータスコードで例外を発生させる

        token_data = response.json()

        if "access_token" not in token_data:
            print("エラー: レスポンスに 'access_token' が見つかりません。")
            print("レスポンス:", response.text)
            return None

        return token_data

    except requests.exceptions.RequestException as e:
        print(f"アクセストークンの取得中にエラーが発生しました: {e}")
        if e.response:
            print(f"レスポンスステータス: {e.response.status_code}")
            print(f"レスポンスボディ: {e.response.text}")
        return None

def call_api(endpoint: str, token: str):
    """
    指定されたアクセストークンを使用して保護されたAPIエンドポイントを呼び出します。
    """
    url = f"{API_BASE_URL}{endpoint}"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    try:
        print(f"\n--- エンドポイント呼び出し: {endpoint} ---")
        response = requests.get(url, headers=headers)
        response.raise_for_status()

        print("ステータスコード:", response.status_code)
        print("レスポンスJSON:")
        # ensure_ascii=Falseで日本語が文字化けしないようにする
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))

    except requests.exceptions.RequestException as e:
        print(f"APIエンドポイント {endpoint} の呼び出し中にエラーが発生しました: {e}")
        if e.response:
            print(f"レスポンスステータス: {e.response.status_code}")
            print(f"レスポンスボディ: {e.response.text}")

if __name__ == "__main__":
    # 認可コードフローを開始するためのURLを生成
    auth_url = (
        f"{KEYCLOAK_SERVER_URL.rstrip('/')}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/auth?"
        f"client_id={KEYCLOAK_CLIENT_ID}&"
        f"response_type=code&"
        f"redirect_uri={REDIRECT_URI}&"
        f"scope=openid"
    )

    print("--- 認可コードの取得手順 ---")
    print(f"1. 次のURLにブラウザでアクセスしてください:\n   {auth_url}")
    print("2. ログイン後、リダイレクト先のURLから 'code=' の後の値をコピーしてください。")
    
    auth_code = input("3. 取得した認可コードをここに貼り付けてEnterキーを押してください: ").strip()

    if auth_code:
        token_data = get_tokens_from_code(auth_code)
        if token_data:
            access_token = token_data.get("access_token")
            print("\nトークンの取得に成功しました。")
            print(f"Access Token:  {access_token[:30]}...")
            print(f"Refresh Token: {token_data.get('refresh_token', 'N/A')[:30]}...")
            call_api("/protected", access_token)
            call_api("/protected/role-required", access_token)
