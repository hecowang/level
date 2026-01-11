#!/usr/bin/env python3
"""
MCP客户端测试脚本
用于测试 stock MCP 接口是否可用
"""
import asyncio
import json
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

try:
    import httpx
except ImportError:
    print("错误: 需要安装 httpx 库")
    print("请运行以下命令之一:")
    print("  pip install httpx")
    print("  或")
    print("  uv add httpx")
    sys.exit(1)


class MCPClient:
    """MCP客户端类"""
    
    def __init__(self, base_url: str = "http://localhost:8000/stock"):
        """
        初始化MCP客户端
        
        Args:
            base_url: 服务器基础URL，默认为 http://localhost:8000/stock
        """
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def close(self):
        """关闭客户端连接"""
        await self.client.aclose()
    
    async def list_tools(self) -> Dict[str, Any]:
        """
        列出所有可用的MCP工具
        
        Returns:
            工具列表
        """
        url = f"{self.base_url}/mcp/v1/tools"
        print(f"\n[测试] GET {url}")
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            tools = response.json()
            print(f"✓ 成功获取 {len(tools)} 个工具")
            return tools
        except Exception as e:
            print(f"✗ 失败: {str(e)}")
            raise
    
    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用MCP工具
        
        Args:
            name: 工具名称
            arguments: 工具参数
        
        Returns:
            工具调用结果
        """
        url = f"{self.base_url}/mcp/v1/tools/call"
        payload = {
            "name": name,
            "arguments": arguments
        }
        print(f"\n[测试] POST {url}")
        print(f"  工具: {name}")
        print(f"  参数: {json.dumps(arguments, ensure_ascii=False, indent=2)}")
        try:
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            if result.get("isError", False):
                print(f"✗ 工具调用返回错误")
                for content in result.get("content", []):
                    if content.get("type") == "text":
                        print(f"  错误信息: {content.get('text')}")
            else:
                print(f"✓ 工具调用成功")
                for content in result.get("content", []):
                    if content.get("type") == "text":
                        text = content.get("text", "")
                        # 只显示前500个字符，避免输出过长
                        if len(text) > 500:
                            print(f"  结果: {text[:500]}...")
                        else:
                            print(f"  结果: {text}")
            return result
        except Exception as e:
            print(f"✗ 失败: {str(e)}")
            raise
    
    async def list_resources(self) -> Dict[str, Any]:
        """
        列出所有可用的MCP资源
        
        Returns:
            资源列表
        """
        url = f"{self.base_url}/mcp/v1/resources"
        print(f"\n[测试] GET {url}")
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            resources = response.json()
            print(f"✓ 成功获取 {len(resources.get('resources', []))} 个资源")
            return resources
        except Exception as e:
            print(f"✗ 失败: {str(e)}")
            raise
    
    async def list_prompts(self) -> Dict[str, Any]:
        """
        列出所有可用的MCP提示词
        
        Returns:
            提示词列表
        """
        url = f"{self.base_url}/mcp/v1/prompts"
        print(f"\n[测试] GET {url}")
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            prompts = response.json()
            print(f"✓ 成功获取 {len(prompts.get('prompts', []))} 个提示词")
            return prompts
        except Exception as e:
            print(f"✗ 失败: {str(e)}")
            raise


async def test_all_endpoints():
    """测试所有MCP端点"""
    print("=" * 60)
    print("MCP客户端测试")
    print("=" * 60)
    
    # 从命令行参数获取base_url，默认为 http://localhost:8000/stock
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000/stock"
    print(f"服务器地址: {base_url}")
    
    client = MCPClient(base_url)
    
    try:
        # 1. 测试列出工具
        print("\n" + "=" * 60)
        print("1. 测试列出工具")
        print("=" * 60)
        tools = await client.list_tools()
        print(f"\n可用工具:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")
        
        # 2. 测试调用工具 - get_stock_data
        print("\n" + "=" * 60)
        print("2. 测试调用工具 - get_stock_data")
        print("=" * 60)
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        await client.call_tool(
            "get_stock_data",
            {
                "code": "sh.600000",
                "start_date": start_date,
                "end_date": end_date
            }
        )
        
        # 3. 测试调用工具 - get_hs300_stocks
        print("\n" + "=" * 60)
        print("3. 测试调用工具 - get_hs300_stocks")
        print("=" * 60)
        await client.call_tool("get_hs300_stocks", {})
        
        # 4. 测试调用工具 - get_zz500_stocks
        print("\n" + "=" * 60)
        print("4. 测试调用工具 - get_zz500_stocks")
        print("=" * 60)
        await client.call_tool("get_zz500_stocks", {})
        
        # 5. 测试列出资源
        print("\n" + "=" * 60)
        print("5. 测试列出资源")
        print("=" * 60)
        resources = await client.list_resources()
        print(f"\n可用资源:")
        for resource in resources.get("resources", []):
            print(f"  - {resource['name']} ({resource['uri']})")
        
        # 6. 测试列出提示词
        print("\n" + "=" * 60)
        print("6. 测试列出提示词")
        print("=" * 60)
        prompts = await client.list_prompts()
        print(f"\n可用提示词:")
        for prompt in prompts.get("prompts", []):
            print(f"  - {prompt['name']}: {prompt['description']}")
        
        print("\n" + "=" * 60)
        print("✓ 所有测试完成!")
        print("=" * 60)
        
    except httpx.ConnectError as e:
        print(f"\n✗ 连接失败: 无法连接到服务器 {base_url}")
        print("  请确保服务器正在运行")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(test_all_endpoints())

