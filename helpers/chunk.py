def chunk(text: str, size: int = 2000) -> list[str]:
    """
    Quebra uma string em pedaços menores baseado no tamanho especificado.

    Args:
        text (str): O texto a ser quebrado
        size (int): Tamanho máximo de cada pedaço (padrão: 2000)

    Returns:
        list[str]: Lista de strings com os pedaços
    """
    if not text:
        return []

    if len(text) <= size:
        return [text]

    chunks = []

    # Quebra em pedaços do tamanho especificado
    for i in range(0, len(text), size):
        chunk_text = text[i:i + size]
        chunks.append(chunk_text)

    return chunks


def smart_chunk(text: str, size: int = 2000) -> list[str]:
    """
    Versão mais inteligente que tenta quebrar em limites de palavras/sentenças.

    Args:
        text (str): O texto a ser quebrado
        size (int): Tamanho máximo de cada pedaço (padrão: 2000)

    Returns:
        list[str]: Lista de strings com os pedaços
    """
    if not text:
        return []

    if len(text) <= size:
        return [text]

    chunks = []
    current_chunk = ""

    # Quebra por parágrafos primeiro
    paragraphs = text.split('\n\n')

    for paragraph in paragraphs:
        # Se o parágrafo inteiro cabe no chunk atual
        if len(current_chunk) + len(paragraph) + 2 <= size:
            current_chunk += ('\n\n' if current_chunk else '') + paragraph
        else:
            # Salva o chunk atual se não estiver vazio
            if current_chunk:
                chunks.append(current_chunk)

            # Se o parágrafo é maior que o tamanho máximo, quebra por sentenças
            if len(paragraph) > size:
                sentences = paragraph.split('. ')
                temp_chunk = ""

                for sentence in sentences:
                    if len(temp_chunk) + len(sentence) + 2 <= size:
                        temp_chunk += ('. ' if temp_chunk else '') + sentence
                    else:
                        if temp_chunk:
                            chunks.append(temp_chunk)

                        # Se a sentença ainda é muito grande, quebra por palavras
                        if len(sentence) > size:
                            words = sentence.split(' ')
                            word_chunk = ""

                            for word in words:
                                if len(word_chunk) + len(word) + 1 <= size:
                                    word_chunk += (' ' if word_chunk else '') + word
                                else:
                                    if word_chunk:
                                        chunks.append(word_chunk)
                                    word_chunk = word

                            if word_chunk:
                                temp_chunk = word_chunk
                            else:
                                temp_chunk = ""
                        else:
                            temp_chunk = sentence

                current_chunk = temp_chunk
            else:
                current_chunk = paragraph

    # Adiciona o último chunk se houver
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def markdown_aware_chunk(text: str, size: int = 2000) -> list[str]:
    """
    Versão que preserva formatação Markdown (inspirada no seu SmartChunker).

    Args:
        text (str): O texto a ser quebrado
        size (int): Tamanho máximo de cada pedaço (padrão: 2000)

    Returns:
        list[str]: Lista de strings com os pedaços
    """
    if not text:
        return []

    if len(text) <= size:
        return [text]

    chunks = []
    current_chunk = ""
    in_code_block = False

    lines = text.split('\n')

    for line in lines:
        # Detecta blocos de código
        if line.strip().startswith('```'):
            in_code_block = not in_code_block

        # Verifica se adicionar esta linha excederia o tamanho
        new_chunk = current_chunk + ('\n' if current_chunk else '') + line

        if len(new_chunk) > size and not in_code_block and current_chunk:
            # Salva o chunk atual e inicia um novo
            chunks.append(current_chunk)
            current_chunk = line
        else:
            current_chunk = new_chunk

    # Adiciona o último chunk
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


# Exemplos de uso
if __name__ == "__main__":
    # Texto de exemplo
    long_text = """
    Este é um texto muito longo que precisa ser quebrado em pedaços menores 
    para poder ser enviado através de sistemas que têm limitações de tamanho.

    O Gino é um bot excepcionalmente inteligente que integra GitLab com Discord.
    Ele possui funcionalidades como dashboard interativo, monitoramento AWS,
    sistema de notificações e gerenciamento de projetos.

    ```python
    def exemplo():
        return "Este é um bloco de código"
    ```

    Mais texto aqui para demonstrar como o sistema funciona...
    """ * 10  # Multiplica para criar um texto bem longo

    print("=== CHUNK SIMPLES ===")
    simple_chunks = chunk(long_text, 200)
    for i, chunk_text in enumerate(simple_chunks):
        print(f"Chunk {i + 1}: {len(chunk_text)} caracteres")
        print(f"Preview: {chunk_text[:50]}...")
        print()

    print("=== SMART CHUNK ===")
    smart_chunks = smart_chunk(long_text, 200)
    for i, chunk_text in enumerate(smart_chunks):
        print(f"Chunk {i + 1}: {len(chunk_text)} caracteres")
        print(f"Preview: {chunk_text[:50]}...")
        print()

    print("=== MARKDOWN AWARE CHUNK ===")
    markdown_chunks = markdown_aware_chunk(long_text, 200)
    for i, chunk_text in enumerate(markdown_chunks):
        print(f"Chunk {i + 1}: {len(chunk_text)} caracteres")
        print(f"Preview: {chunk_text[:50]}...")
        print()