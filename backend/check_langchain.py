try:
    import langchain
    print("LangChain is installed")
except ImportError:
    print("LangChain is NOT installed")
except Exception as e:
    print(f"Error importing LangChain: {e}")
