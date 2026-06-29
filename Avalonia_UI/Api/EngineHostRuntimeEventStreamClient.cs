using System;
using System.IO;
using System.Net.WebSockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Models;

namespace Avalonia_UI.Api;

public sealed class EngineHostRuntimeEventStreamClient
{
    public Uri BuildEventsUri(EngineHostConnectionSettings settings)
    {
        return settings.BuildRuntimeEventsWebSocketUri();
    }

    public async Task<EngineHostRuntimeEventStream> ConnectAsync(
        EngineHostConnectionSettings settings,
        CancellationToken cancellationToken = default)
    {
        var webSocket = new ClientWebSocket();
        await webSocket.ConnectAsync(BuildEventsUri(settings), cancellationToken);
        return new EngineHostRuntimeEventStream(webSocket);
    }
}

public sealed class EngineHostRuntimeEventStream : IAsyncDisposable
{
    private readonly ClientWebSocket _webSocket;

    public EngineHostRuntimeEventStream(ClientWebSocket webSocket)
    {
        _webSocket = webSocket;
    }

    public async Task<RuntimeEventDto?> ReadNextAsync(
        CancellationToken cancellationToken = default)
    {
        var buffer = new byte[8192];
        using var content = new MemoryStream();
        WebSocketReceiveResult result;
        do
        {
            result = await _webSocket.ReceiveAsync(buffer, cancellationToken);
            if (result.MessageType == WebSocketMessageType.Close)
            {
                return null;
            }

            content.Write(buffer, 0, result.Count);
        }
        while (!result.EndOfMessage);

        if (result.MessageType != WebSocketMessageType.Text)
        {
            return null;
        }

        var json = Encoding.UTF8.GetString(content.ToArray());
        return ParseRuntimeEvent(json);
    }

    public static RuntimeEventDto ParseRuntimeEvent(string json)
    {
        return JsonSerializer.Deserialize<RuntimeEventDto>(json, FlowWeaverJson.Options)
            ?? throw new JsonException("Runtime event payload was empty.");
    }

    public async ValueTask DisposeAsync()
    {
        if (_webSocket.State is WebSocketState.Open or WebSocketState.CloseReceived)
        {
            await _webSocket.CloseAsync(
                WebSocketCloseStatus.NormalClosure,
                "Client disposed.",
                CancellationToken.None);
        }

        _webSocket.Dispose();
    }
}
