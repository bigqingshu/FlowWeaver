using System.Text.Json.Serialization;

namespace Avalonia_UI.Api;

public sealed record ApiResponseEnvelope<TData>
{
    [JsonPropertyName("ok")]
    public bool Ok { get; init; }

    [JsonPropertyName("data")]
    public TData? Data { get; init; }

    [JsonPropertyName("error")]
    public ApiErrorDto? Error { get; init; }

    [JsonPropertyName("request_id")]
    public string RequestId { get; init; } = string.Empty;

    public static ApiResponseEnvelope<TData> Failure(
        string errorCode,
        string message,
        string requestId = "client",
        bool retryable = false)
    {
        return new ApiResponseEnvelope<TData>
        {
            Ok = false,
            Error = new ApiErrorDto
            {
                ErrorCode = errorCode,
                Message = message,
                Retryable = retryable,
            },
            RequestId = requestId,
        };
    }

    public static ApiResponseEnvelope<TData> Success(
        TData data,
        string requestId = "client")
    {
        return new ApiResponseEnvelope<TData>
        {
            Ok = true,
            Data = data,
            RequestId = requestId,
        };
    }
}
