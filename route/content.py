from flask import Blueprint, jsonify, request, abort
from app import db
from app.models.admin import SiteSetting, Banner


content_bp = Blueprint('content_bp', __name__)


@content_bp.get('/settings')
def get_settings():
    """
    GET /content/settings
    - Optional query param: key=<key_name> to fetch a single setting
    """
    key = request.args.get('key')
    if key:
        setting = db.session.query(SiteSetting).filter_by(key=key).first()
        if not setting:
            abort(404, description='Setting not found')
        return jsonify({
            'id': setting.id,
            'key': setting.key,
            'value': setting.value,
            'value_type': setting.value_type,
            'updated_at': setting.updated_at.isoformat() if setting.updated_at else None,
        })
    settings = db.session.query(SiteSetting).all()
    return jsonify([
        {
            'id': s.id,
            'key': s.key,
            'value': s.value,
            'value_type': s.value_type,
            'updated_at': s.updated_at.isoformat() if s.updated_at else None,
        }
        for s in settings
    ])


@content_bp.get('/banners')
def get_banners():
    """
    GET /content/banners
    - Returns active banners ordered by sort_order then created_at desc
    """
    banners = (
        db.session.query(Banner)
        .filter(Banner.is_active.is_(True))
        .order_by(Banner.sort_order.asc(), Banner.created_at.desc())
        .all()
    )
    return jsonify([
        {
            'id': b.id,
            'title': b.title,
            'image_url': b.image_url,
            'link_url': b.link_url,
            'is_active': b.is_active,
            'sort_order': b.sort_order,
            'created_at': b.created_at.isoformat() if b.created_at else None,
            'updated_at': b.updated_at.isoformat() if b.updated_at else None,
        }
        for b in banners
    ])


