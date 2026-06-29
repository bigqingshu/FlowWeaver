using System;
using System.Linq;
using System.Text.RegularExpressions;

namespace Avalonia_UI.Api;

public static class EngineHostConnectionDiagnostics
{
    private const string TokenInvalidMessage =
        "EngineHost token is wrong, rotated, or no longer valid. Re-enter the current local API token.";

    public static string DescribeError<TData>(ApiResponseEnvelope<TData> response)
    {
        if (response.Error is null)
        {
            return "EngineHost response did not include data.";
        }

        return response.Error.ErrorCode switch
        {
            "TOKEN_REQUIRED" => "EngineHost token is required.",
            "UNAUTHORIZED" => TokenInvalidMessage,
            "INVALID_BASE_URL" => $"EngineHost base URL is invalid: {response.Error.Message}",
            "REQUEST_TIMEOUT" => "EngineHost request timed out. Check that EngineHost is still running.",
            "REQUEST_FAILED" => $"EngineHost request failed: {response.Error.Message}",
            _ => $"{response.Error.ErrorCode}: {response.Error.Message}",
        };
    }

    public static string DescribeRuntimeEventStreamException(Exception exception)
    {
        var message = RedactToken(exception.Message);
        return $"RuntimeEvent stream connection failed: {message}";
    }

    public static string RedactToken(string value)
    {
        if (string.IsNullOrEmpty(value))
        {
            return value;
        }

        if (!Uri.TryCreate(value, UriKind.Absolute, out var uri))
        {
            return Regex.Replace(
                value,
                "(?i)(token=)[^&\\s]+",
                "$1***");
        }

        return RedactToken(uri).ToString();
    }

    public static Uri RedactToken(Uri uri)
    {
        if (string.IsNullOrEmpty(uri.Query))
        {
            return uri;
        }

        var query = string.Join(
            "&",
            uri.Query
                .TrimStart('?')
                .Split('&', StringSplitOptions.RemoveEmptyEntries)
                .Select(part =>
                {
                    var separatorIndex = part.IndexOf('=');
                    var key = separatorIndex < 0 ? part : part[..separatorIndex];
                    return string.Equals(
                        Uri.UnescapeDataString(key),
                        "token",
                        StringComparison.OrdinalIgnoreCase)
                            ? $"{key}=***"
                            : part;
                }));

        return new UriBuilder(uri)
        {
            Query = query,
        }.Uri;
    }
}
