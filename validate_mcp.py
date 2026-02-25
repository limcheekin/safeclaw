import asyncio
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

async def main():
    url = "http://localhost:8000/sse"
    print(f"Connecting to MCP server at {url}...")
    import jwt
    token = jwt.encode({"sub": "admin", "roles": ["admin"]}, "secret", algorithm="HS256")
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        async with sse_client(url, headers=headers) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                print("Session initialized.")
                
                tools = await session.list_tools()
                print("\nDiscovered tools:")
                for i, tool in enumerate(tools.tools):
                    print(f"{i+1}. {tool.name}: {tool.description}")
                print()
                
                # Test the tools
                
                print("1. Testing get_weather...")
                try:
                    result = await session.call_tool("get_weather", arguments={"location": "London"})
                    print(f"Result: {result}")
                except Exception as e:
                    print(f"Failed: {e}")
                    
                print("\n2. Testing crawl_url...")
                try:
                    result = await session.call_tool("crawl_url", arguments={"url": "https://example.com", "depth": 0})
                    print(f"Result: {result}")
                except Exception as e:
                    print(f"Failed: {e}")
                
                print("\n3. Testing summarize_content...")
                try:
                    result = await session.call_tool("summarize_content", arguments={"target": "This is a short test of the summarizer.", "sentences": 1})
                    print(f"Result: {result}")
                except Exception as e:
                    print(f"Failed: {e}")
                
                print("\n4. Testing admin_flush_cache...")
                try:
                    result = await session.call_tool("admin_flush_cache", arguments={})
                    print(f"Result: {result}")
                except Exception as e:
                    print(f"Failed: {e}")
                
    except Exception as e:
        print(f"Error connecting to the server: {e}")

if __name__ == "__main__":
    asyncio.run(main())
