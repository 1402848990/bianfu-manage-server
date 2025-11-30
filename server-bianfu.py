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
    account = Column(String(255), nullable=False, unique=True)
    status = Column(Enum('unused', 'used'), default='unused')
    created_at = Column(DateTime, default=datetime.utcnow)
    extracted_by = Column(String(255), nullable=True)
    extracted_at = Column(DateTime, nullable=True)


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
    if not isinstance(data, list):
        return jsonify({"error": "Expected a list of account strings"}), 400

    # Step 1: 提取并清洗非空字符串账号
    raw_accounts = [acc.strip() for acc in data if isinstance(acc, str) and acc.strip()]
    if not raw_accounts:
        return jsonify({"error": "无效账号"}), 400

    # Step 2: 去除当前批次内的重复（保留顺序可选，这里用 dict.fromkeys 保持插入顺序）
    unique_in_batch = list(dict.fromkeys(raw_accounts))  # Python 3.7+ 保持顺序

    session = SessionLocal()
    try:
        # Step 3: 查询数据库中已存在的账号
        existing_in_db = session.query(Account.account).filter(
            Account.account.in_(unique_in_batch)
        ).all()
        existing_set = {row[0] for row in existing_in_db}

        # Step 4: 过滤出真正需要插入的新账号
        new_accounts = [
            Account(account=acc) for acc in unique_in_batch if acc not in existing_set
        ]

        if new_accounts:
            session.bulk_save_objects(new_accounts)
            session.commit()
            added = len(new_accounts)
        else:
            added = 0

        skipped_total = len(raw_accounts) - added  # 包括批次内重复 + 数据库已有
        return jsonify({
            "message": f"{added}个账号添加成功！",
            "skipped_due_to_duplicate_or_exist": skipped_total
        }), 201

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
    app.run(host='0.0.0.0', port=5500, debug=True)
