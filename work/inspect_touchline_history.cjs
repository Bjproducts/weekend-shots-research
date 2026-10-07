const root='C:/Users/bjpro/Documents/Codex/2026-09-14/files-pasted-by-the-user-build/outputs/soccer-analytics';
process.loadEnvFile(root+'/.env.local');
const {Client}=require(root+'/node_modules/pg');
(async()=>{const c=new Client({connectionString:process.env.DATABASE_URL,connectionTimeoutMillis:4000,statement_timeout:10000});try {
await c.connect();await c.query('BEGIN READ ONLY');
console.log(JSON.stringify((await c.query("select table_name,column_name from information_schema.columns where table_schema='public' order by table_name,ordinal_position")).rows));
await c.query('ROLLBACK');
}catch(e){console.log(JSON.stringify({status:'unavailable',code:e.code||'unknown'}));}finally{await c.end();}})();
