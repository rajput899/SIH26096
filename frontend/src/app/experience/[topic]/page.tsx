import Exhibition from '../../../components/Exhibition';
export default async function Topic({params}:{params:Promise<{topic:string}>}) {
 const {topic}=await params;
 let label=topic;
 try { label=decodeURIComponent(topic); } catch { /* Keep malformed route text readable. */ }
 return <Exhibition topic={label}/>;
}
