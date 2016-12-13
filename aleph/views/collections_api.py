from flask import Blueprint, request
from apikit import obj_or_404, jsonify, Pager, request_data, arg_bool

from aleph.core import USER_QUEUE, USER_ROUTING_KEY
from aleph.model import Collection, db
from aleph.events import log_event
from aleph.logic import delete_collection, update_collection
from aleph.logic import analyze_collection
from aleph.text import latinize_text

blueprint = Blueprint('collections_api', __name__)


@blueprint.route('/api/1/collections', methods=['GET'])
def index():
    # allow to filter for writeable collections only, needed
    # in some UI scenarios:
    permission = request.args.get('permission')
    if permission not in [request.authz.READ, request.authz.WRITE]:
        permission = request.authz.READ
    collections = request.authz.collections[permission]

    # Other filters for navigation
    label = request.args.get('label')
    countries = request.args.getlist('countries')
    category = request.args.getlist('category')
    managed = arg_bool('managed', True) if 'managed' in request.args else None

    # Include counts (of entities, documents) in list view?
    counts = arg_bool('counts', False)

    def converter(colls):
        return [c.to_dict(counts=counts) for c in colls]

    facet = [f.lower().strip() for f in request.args.getlist('facet')]
    q = Collection.find(label=label, countries=countries, category=category,
                        collection_id=collections, managed=managed)
    data = Pager(q).to_dict(results_converter=converter)
    facets = {}
    if 'countries' in facet:
        facets['countries'] = Collection.facet_by(q, Collection.countries)
    if 'category' in facet:
        facets['category'] = Collection.facet_by(q, Collection.category)
    data['facets'] = facets
    return jsonify(data)


@blueprint.route('/api/1/collections', methods=['POST', 'PUT'])
def create():
    request.authz.require(request.authz.logged_in)
    data = request_data()
    data['managed'] = False
    collection = Collection.create(data, request.authz.role)
    db.session.commit()
    update_collection(collection)
    log_event(request)
    return jsonify(collection)


@blueprint.route('/api/1/collections/<int:id>', methods=['GET'])
def view(id):
    collection = obj_or_404(Collection.by_id(id))
    request.authz.require(request.authz.collection_read(collection))
    data = collection.to_dict(counts=True)
    # data.update(collection.content_statistics())
    return jsonify(data)


@blueprint.route('/api/1/collections/<int:id>', methods=['POST', 'PUT'])
def update(id):
    collection = obj_or_404(Collection.by_id(id))
    request.authz.require(request.authz.collection_write(collection))
    collection.update(request_data())
    db.session.add(collection)
    db.session.commit()
    update_collection(collection)
    log_event(request)
    return view(id)


@blueprint.route('/api/1/collections/<int:id>/process',
                 methods=['POST', 'PUT'])
def process(id):
    collection = obj_or_404(Collection.by_id(id))
    request.authz.require(request.authz.collection_write(collection))
    analyze_collection.apply_async([collection.id], queue=USER_QUEUE,
                                   routing_key=USER_ROUTING_KEY)
    log_event(request)
    return jsonify({'status': 'ok'})


@blueprint.route('/api/1/collections/<int:id>/pending', methods=['GET'])
def pending(id):
    collection = obj_or_404(Collection.by_id(id))
    request.authz.require(request.authz.collection_read(collection))
    q = collection.pending_entities()
    q = q.limit(30)
    entities = []
    for entity in q.all():
        data = entity.to_dict()
        data['name_latin'] = latinize_text(entity.name)
        entities.append(data)
    return jsonify({'results': entities, 'total': len(entities)})


@blueprint.route('/api/1/collections/<int:id>', methods=['DELETE'])
def delete(id):
    collection = obj_or_404(Collection.by_id(id))
    request.authz.require(request.authz.collection_write(collection))
    delete_collection.apply_async([collection.id], queue=USER_QUEUE,
                                  routing_key=USER_ROUTING_KEY)
    log_event(request)
    return jsonify({'status': 'ok'})
