using System.Text.Json;
using System.Text.Json.Serialization;

namespace Avalonia_UI.Api;

public sealed record ApiErrorDto
{
    [JsonPropertyName("error_code")]
    public string ErrorCode { get; init; } = string.Empty;

    [JsonPropertyName("message")]
    public string Message { get; init; } = string.Empty;

    [JsonPropertyName("details")]
    public JsonElement Details { get; init; }

    [JsonPropertyName("retryable")]
    public bool Retryable { get; init; }
}
