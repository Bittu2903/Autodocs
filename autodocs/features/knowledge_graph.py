from neo4j import GraphDatabase
from typing import List, Dict, Any

class KnowledgeGraph:
    """Manages the knowledge graph in Neo4j"""
    
    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        self.driver.close()
    
    def create_code_entity(self, entity_type: str, properties: Dict[str, Any]):
        """Create a code entity node (Service, Module, Class, Function, API)"""
        with self.driver.session() as session:
            query = f"""
            CREATE (n:{entity_type} $props)
            RETURN n
            """
            result = session.run(query, props=properties)
            return result.single()
    
    def create_relationship(self, from_id: str, to_id: str, rel_type: str, properties: Dict = None):
        """Create relationship between entities"""
        with self.driver.session() as session:
            props = properties or {}
            query = """
            MATCH (a {id: $from_id})
            MATCH (b {id: $to_id})
            CREATE (a)-[r:%s $props]->(b)
            RETURN r
            """ % rel_type
            result = session.run(query, from_id=from_id, to_id=to_id, props=props)
            return result.single()
    
    def store_analysis(self, repo_id: str, analysis: Dict[str, Any]):
        """Store complete code analysis in graph"""
        with self.driver.session() as session:
            # Create repository node
            session.run("""
                MERGE (r:Repository {id: $repo_id})
                SET r += $props
            """, repo_id=repo_id, props={"language": analysis.get("language")})
            
            # Create module nodes
            for module in analysis.get("modules", []):
                module_id = f"{repo_id}:module:{module['path']}"
                session.run("""
                    MERGE (m:Module {id: $module_id})
                    SET m.name = $name, m.path = $path, m.docstring = $doc
                    WITH m
                    MATCH (r:Repository {id: $repo_id})
                    MERGE (r)-[:CONTAINS]->(m)
                """, module_id=module_id, name=module['name'], 
                    path=module['path'], doc=module.get("docstring"), repo_id=repo_id)
                
                # Create class nodes
                for cls in module.get("classes", []):
                    class_id = f"{module_id}:{cls['name']}"
                    session.run("""
                        MERGE (c:Class {id: $class_id})
                        SET c.name = $name, c.docstring = $doc
                        WITH c
                        MATCH (m:Module {id: $module_id})
                        MERGE (m)-[:DEFINES]->(c)
                    """, class_id=class_id, name=cls['name'], doc=cls.get("docstring"),
                        module_id=module_id)
                
                # Create function nodes
                for fn in module.get("functions", []):
                    func_id = f"{module_id}:func:{fn['name']}"
                    session.run("""
                        MERGE (f:Function {id: $func_id})
                        SET f.name = $name, f.args = $args, f.docstring = $doc, f.path = $path, f.returns = $returns
                        WITH f
                        MATCH (m:Module {id: $module_id})
                        MERGE (m)-[:DEFINES]->(f)
                    """, func_id=func_id, name=fn['name'], args=fn.get("args"),
                        doc=fn.get("docstring"), path=module['path'], returns=fn.get("returns"),
                        module_id=module_id)
            
            # Create API nodes
            for api in analysis.get("apis", []):
                api_id = f"{repo_id}:api:{api['endpoint']}"
                session.run("""
                    MERGE (a:API {id: $api_id})
                    SET a.endpoint = $endpoint, a.type = $type, a.file = $file
                    WITH a
                    MATCH (r:Repository {id: $repo_id})
                    MERGE (r)-[:EXPOSES]->(a)
                """, api_id=api_id, endpoint=api['endpoint'], 
                    type=api.get('type'), file=api.get('file'), repo_id=repo_id)
            
            # Store CALLS edges
            for edge in analysis.get("call_edges", []):
                src = f"{repo_id}:module:{edge['from'].split('::')[0]}:func:{edge['from'].split('::')[1]}"
                tgt = f"{repo_id}:module:{edge['to'].split('::')[0]}:func:{edge['to'].split('::')[1]}"
                session.run("""
                    MATCH (a:Function {id: $src})
                    MATCH (b:Function {id: $tgt})
                    MERGE (a)-[:CALLS]->(b)
                """, src=src, tgt=tgt)
            
            # Feature nodes
            for feat in analysis.get("features", []):
                feat_id = f"{repo_id}:feature:{feat['name']}"
                session.run("""
                    MERGE (ft:Feature {id: $feat_id})
                    SET ft.name = $name
                    WITH ft
                    MATCH (r:Repository {id: $repo_id})
                    MERGE (r)-[:HAS_FEATURE]->(ft)
                """, feat_id=feat_id, name=feat['name'], repo_id=repo_id)
                for fref in feat.get("functions", []):
                    func_id = f"{repo_id}:module:{fref.split('::')[0]}:func:{fref.split('::')[1]}"
                    session.run("""
                        MATCH (ft:Feature {id: $feat_id})
                        MATCH (fn:Function {id: $func_id})
                        MERGE (ft)-[:INCLUDES]->(fn)
                    """, feat_id=feat_id, func_id=func_id)
    
    def find_dependencies(self, entity_id: str) -> List[Dict]:
        """Find all dependencies of an entity"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n {id: $entity_id})-[:DEPENDS_ON]->(dep)
                RETURN dep
            """, entity_id=entity_id)
            return [record["dep"] for record in result]
    
    def find_impact(self, entity_id: str) -> List[Dict]:
        """Find all entities impacted by changes to this entity"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n {id: $entity_id})<-[:DEPENDS_ON*1..3]-(impacted)
                RETURN DISTINCT impacted
            """, entity_id=entity_id)
            return [record["impacted"] for record in result]
    
    def get_architecture_overview(self, repo_id: str) -> Dict[str, Any]:
        """Get high-level architecture view"""
        with self.driver.session() as session:
            # Get services/modules
            modules = session.run("""
                MATCH (r:Repository {id: $repo_id})-[:CONTAINS]->(m:Module)
                RETURN m.name as name, m.path as path
            """, repo_id=repo_id)
            
            # Get APIs
            apis = session.run("""
                MATCH (r:Repository {id: $repo_id})-[:EXPOSES]->(a:API)
                RETURN a.endpoint as endpoint, a.type as type
            """, repo_id=repo_id)
            
            return {
                "modules": [dict(r) for r in modules],
                "apis": [dict(r) for r in apis]
            }

    def delete_repository(self, repo_id: str):
        with self.driver.session() as session:
            session.run("""
                MATCH (r:Repository {id: $repo_id})
                OPTIONAL MATCH (r)-[:CONTAINS]->(m:Module)
                OPTIONAL MATCH (r)-[:EXPOSES]->(a:API)
                OPTIONAL MATCH (r)-[:HAS_FEATURE]->(ft:Feature)
                OPTIONAL MATCH (ft)-[:INCLUDES]->(fn:Function)
                OPTIONAL MATCH (m)-[:DEFINES]->(fn2:Function)
                OPTIONAL MATCH (m)-[:DEFINES]->(c:Class)
                DETACH DELETE fn
                DETACH DELETE fn2
                DETACH DELETE c
                DETACH DELETE m
                DETACH DELETE a
                DETACH DELETE ft
                DETACH DELETE r
            """, repo_id=repo_id)

    def get_graph(self, repo_id: str, limit: int = 500) -> Dict[str, Any]:
        with self.driver.session() as session:
            nodes_result = session.run("""
                MATCH (r:Repository {id: $repo_id})
                OPTIONAL MATCH (r)-[:CONTAINS]->(m:Module)
                OPTIONAL MATCH (m)-[:DEFINES]->(f:Function)
                OPTIONAL MATCH (m)-[:DEFINES]->(c:Class)
                OPTIONAL MATCH (r)-[:EXPOSES]->(a:API)
                OPTIONAL MATCH (r)-[:HAS_FEATURE]->(ft:Feature)
                RETURN COLLECT(DISTINCT {id: r.id, label: 'Repository', type: 'Repository', doc: ''}) +
                       COLLECT(DISTINCT {id: m.id, label: m.name, type: 'Module', doc: coalesce(m.docstring,'')}) +
                       COLLECT(DISTINCT {id: f.id, label: f.name, type: 'Function', doc: coalesce(f.docstring,'')}) +
                       COLLECT(DISTINCT {id: c.id, label: c.name, type: 'Class', doc: coalesce(c.docstring,'')}) +
                       COLLECT(DISTINCT {id: a.id, label: a.endpoint, type: 'API', doc: ''}) +
                       COLLECT(DISTINCT {id: ft.id, label: ft.name, type: 'Feature', doc: ''}) AS nodes
            """, repo_id=repo_id)
            nodes = nodes_result.single()["nodes"]
            links_result = session.run("""
                MATCH (r:Repository {id: $repo_id})-[:CONTAINS]->(m:Module)
                OPTIONAL MATCH (m)-[:DEFINES]->(f:Function)
                OPTIONAL MATCH (m)-[:DEFINES]->(c:Class)
                OPTIONAL MATCH (f)-[rel:CALLS]->(f2:Function)
                OPTIONAL MATCH (r)-[:EXPOSES]->(a:API)
                OPTIONAL MATCH (r)-[:HAS_FEATURE]->(ft:Feature)
                OPTIONAL MATCH (ft)-[:INCLUDES]->(f3:Function)
                RETURN
                  COLLECT(DISTINCT {source: r.id, target: m.id, rel: 'CONTAINS'}) +
                  COLLECT(DISTINCT {source: m.id, target: f.id, rel: 'DEFINES'}) +
                  COLLECT(DISTINCT {source: m.id, target: c.id, rel: 'DEFINES'}) +
                  COLLECT(DISTINCT {source: f.id, target: f2.id, rel: 'CALLS'}) +
                  COLLECT(DISTINCT {source: r.id, target: a.id, rel: 'EXPOSES'}) +
                  COLLECT(DISTINCT {source: r.id, target: ft.id, rel: 'HAS_FEATURE'}) +
                  COLLECT(DISTINCT {source: ft.id, target: f3.id, rel: 'INCLUDES'}) AS links
            """, repo_id=repo_id)
            links = links_result.single()["links"]
            # Limit nodes/links for initial view
            return {"nodes": nodes[:limit], "links": links[:limit]}

    def get_neighbors(self, node_id: str) -> Dict[str, Any]:
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n {id: $node_id})-[r]-(m)
                RETURN DISTINCT {id: m.id, label: coalesce(m.name, coalesce(m.endpoint, '')), type: labels(m)[0], doc: coalesce(m.docstring,'')} AS node,
                                {source: n.id, target: m.id, rel: type(r)} AS link
            """, node_id=node_id)
            nodes = []
            links = []
            for record in result:
                nodes.append(record["node"])
                links.append(record["link"])
            return {"nodes": nodes, "links": links}
