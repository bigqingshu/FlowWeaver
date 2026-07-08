using System.Text.Json;
using Avalonia_UI.Api;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private string DescribeError<TData>(ApiResponseEnvelope<TData> response)
    {
        if (response.Error is null)
        {
            return T("diagnostics.response_missing_data");
        }

        if (response.Error.ErrorCode is "TOKEN_REQUIRED" or "UNAUTHORIZED")
        {
            IsAuthenticationFailed = true;
        }

        return response.Error.ErrorCode switch
        {
            "TOKEN_REQUIRED" => T("diagnostics.token_required"),
            "UNAUTHORIZED" => T("diagnostics.token_invalid"),
            "INVALID_BASE_URL" => F(
                "format.diagnostics.invalid_base_url",
                response.Error.Message),
            "REQUEST_TIMEOUT" => T("diagnostics.request_timeout"),
            "REQUEST_FAILED" => F(
                "format.diagnostics.request_failed",
                response.Error.Message),
            "WORKFLOW_VALIDATION_FAILED" =>
                FormatWorkflowValidationErrorDetails(response.Error)
                ?? $"{response.Error.ErrorCode}: {response.Error.Message}",
            _ => $"{response.Error.ErrorCode}: {response.Error.Message}",
        };
    }

    private static string? FormatWorkflowValidationErrorDetails(ApiErrorDto error)
    {
        if (error.Details.ValueKind is JsonValueKind.Undefined or JsonValueKind.Null)
        {
            return null;
        }

        try
        {
            var validation = error.Details.Deserialize<WorkflowValidationResultDto>(
                FlowWeaverJson.Options);
            return validation is null ? null : FormatValidationIssues(validation);
        }
        catch (JsonException)
        {
            return null;
        }
    }
}
