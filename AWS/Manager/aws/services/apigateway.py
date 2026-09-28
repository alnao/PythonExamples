"""API Gateway: API REST (v1) con risorse e stage, API HTTP e WebSocket (v2) con route e stage."""

from aws.services import paginate


class AwsApiGateway:
    def __init__(self, session):
        self.client = session.client('apigateway')
        self.v2 = session.client('apigatewayv2')

    def apis(self):
        """API REST e HTTP/WebSocket insieme; 'apiType' dice quale API di AWS usare per il dettaglio."""
        rest = [{**a, 'apiType': 'REST'} for a in paginate(self.client, 'get_rest_apis', 'items')]
        http = [{'id': a['ApiId'], 'name': a['Name'], 'description': a.get('Description', ''),
                 'apiType': a.get('ProtocolType', 'HTTP'), **a}
                for a in paginate(self.v2, 'get_apis', 'Items')]
        return rest + http

    def detail(self, api_id, api_type='REST'):
        """Risorse (REST) o route (HTTP/WebSocket), con gli stage, nello stesso formato."""
        if api_type == 'REST':
            resources = [{'path': r.get('path', ''), 'methods': sorted((r.get('resourceMethods') or {}).keys())}
                         for r in paginate(self.client, 'get_resources', 'items', restApiId=api_id)]
            stages = self.client.get_stages(restApiId=api_id).get('item', [])
        else:
            resources = []
            for r in paginate(self.v2, 'get_routes', 'Items', ApiId=api_id):
                method, _, path = r['RouteKey'].partition(' ')
                resources.append({'path': path or r['RouteKey'], 'methods': [method] if path else [],
                                  'target': r.get('Target', '')})
            stages = paginate(self.v2, 'get_stages', 'Items', ApiId=api_id)
            for s in stages:
                s['stageName'] = s.get('StageName', '')
        return {'resources': sorted(resources, key=lambda r: r['path']), 'stages': stages}
