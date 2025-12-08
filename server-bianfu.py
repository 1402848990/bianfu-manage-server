from flask import Flask, request, jsonify
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Enum, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import os

# ----------------------------
# 配置数据库连接
# ----------------------------
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "bianfu")

# 数据库连接地址
DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"

engine = create_engine(DATABASE_URL, echo=False)
Base = declarative_base()
SessionLocal = sessionmaker(bind=engine)

# ----------------------------
# 数据模型
# ----------------------------

# 数据库表字段
class Account(Base):
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    account = Column(String(255), nullable=False)  # ← 移除 unique=True
    status = Column(Enum('unused', 'used'), default='unused')
    created_at = Column(DateTime, default=datetime.utcnow)
    extracted_by = Column(String(255), nullable=True)
    extracted_at = Column(DateTime, nullable=True)

class Blacklist(Base):
    __tablename__ = 'blacklist'

    id = Column(Integer, primary_key=True, autoincrement=True)
    account = Column(String(255), nullable=False, unique=True)  # 黑名单必须唯一
    added_at = Column(DateTime, default=datetime.utcnow)

# 创建表（如果不存在）
Base.metadata.create_all(bind=engine)



# ----------------------------
# Flask App
# ----------------------------
app = Flask(__name__)

# 添加账号接口
@app.route('/add_accounts', methods=['POST'])
def add_accounts():
    data = request.get_json()
    
    # 兼容旧格式（纯列表）和新格式（带参数的对象）
    if isinstance(data, list):
        # 旧客户端：默认启用去重
        accounts_list = data
        disable_dedup = False
    elif isinstance(data, dict):
        accounts_list = data.get('accounts', [])
        disable_dedup = bool(data.get('disable_dedup', False))
    else:
        return jsonify({"error": "Invalid request format"}), 400

    if not isinstance(accounts_list, list):
        return jsonify({"error": "Expected 'accounts' to be a list"}), 400

    raw_accounts = [acc.strip() for acc in accounts_list if isinstance(acc, str) and acc.strip()]
    if not raw_accounts:
        return jsonify({"error": "无效账号"}), 400

    session = SessionLocal()
    try:
        if disable_dedup:
            # ❗ 不去重：直接为每个账号创建新记录（即使重复）
            new_accounts = [Account(account=acc) for acc in raw_accounts]
            session.bulk_save_objects(new_accounts)
            session.commit()
            added = len(new_accounts)
            skipped = 0
        else:
            # ✅ 正常去重逻辑
            unique_in_batch = list(dict.fromkeys(raw_accounts))
            existing_in_db = session.query(Account.account).filter(
                Account.account.in_(unique_in_batch)
            ).all()
            existing_set = {row[0] for row in existing_in_db}
            new_accounts = [
                Account(account=acc) for acc in unique_in_batch if acc not in existing_set
            ]
            if new_accounts:
                session.bulk_save_objects(new_accounts)
                session.commit()
            added = len(new_accounts)
            skipped = len(raw_accounts) - added

        return jsonify({
            "message": f"{added}个账号添加成功！",
            "skipped_due_to_duplicate_or_exist": skipped
        }), 201

    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

# ----------------------------
# 黑名单管理接口
# ----------------------------

@app.route('/blacklist', methods=['GET'])
def get_blacklist():
    session = SessionLocal()
    try:
        blacklist_entries = session.query(Blacklist.account).all()
        accounts = [row[0] for row in blacklist_entries]
        return jsonify({"blacklist": accounts}), 200
    finally:
        session.close()

@app.route('/blacklist', methods=['POST'])
def add_to_blacklist():
    data = request.get_json()
    accounts_list = data.get('accounts', [])
    if not isinstance(accounts_list, list):
        return jsonify({"error": "'accounts' must be a list"}), 400

    raw_accounts = [acc.strip() for acc in accounts_list if isinstance(acc, str) and acc.strip()]
    if not raw_accounts:
        return jsonify({"error": "No valid accounts provided"}), 400

    session = SessionLocal()
    try:
        # 过滤掉已存在的（避免重复报错）
        existing = session.query(Blacklist.account).filter(
            Blacklist.account.in_(raw_accounts)
        ).all()
        existing_set = {row[0] for row in existing}
        new_accounts = [Blacklist(account=acc) for acc in raw_accounts if acc not in existing_set]

        if new_accounts:
            session.bulk_save_objects(new_accounts)
            session.commit()

        return jsonify({
            "message": f"{len(new_accounts)} 个账号加入黑名单",
            "skipped": len(raw_accounts) - len(new_accounts)
        }), 201
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

@app.route('/blacklist/remove', methods=['POST'])
def remove_from_blacklist():
    data = request.get_json()
    accounts_list = data.get('accounts', [])
    if not isinstance(accounts_list, list):
        return jsonify({"error": "'accounts' must be a list"}), 400

    raw_accounts = [acc.strip() for acc in accounts_list if isinstance(acc, str) and acc.strip()]
    if not raw_accounts:
        return jsonify({"error": "No valid accounts provided"}), 400

    session = SessionLocal()
    try:
        deleted_count = session.query(Blacklist).filter(
            Blacklist.account.in_(raw_accounts)
        ).delete(synchronize_session=False)
        session.commit()
        return jsonify({"message": f"成功移除 {deleted_count} 个黑名单账号"}), 200
    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()

# 账号状态
@app.route('/stats', methods=['GET'])
def stats():
    session = SessionLocal()
    try:
        total = session.query(Account).count()
        used = session.query(Account).filter(Account.status == 'used').count()
        unused = total - used
        return jsonify({
            "total": total,
            "used": used,
            "unused": unused
        }), 200
    finally:
        session.close()

# 提取账号接口
@app.route('/extract', methods=['POST'])
def extract_accounts():
    data = request.get_json()
    count = data.get('count')
    extractor = data.get('extractor')

    if not isinstance(count, int) or count <= 0:
        return jsonify({"error": "'count' must be a positive integer"}), 400
    if not isinstance(extractor, str) or not extractor.strip():
        return jsonify({"error": "'extractor' must be a non-empty string"}), 400

    extractor = extractor.strip()
    session = SessionLocal()
    try:
        # 锁定并更新若干未使用的账号（防止并发重复提取）
        accounts = session.query(Account).filter(
            Account.status == 'unused'
        ).limit(count).with_for_update().all()

        if not accounts:
            return jsonify({"error": "No unused accounts available"}), 404

        now = datetime.utcnow()
        extracted_list = []
        for acc in accounts:
            acc.status = 'used'
            acc.extracted_by = extractor
            acc.extracted_at = now
            extracted_list.append(acc.account)

        session.commit()

        return jsonify({
            "extracted_count": len(extracted_list),
            "accounts": extracted_list,
            "extractor": extractor,
            "extracted_at": now.isoformat()
        }), 200

    except Exception as e:
        session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        session.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
