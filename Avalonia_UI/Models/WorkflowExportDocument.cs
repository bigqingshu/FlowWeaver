using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;
using Avalonia_UI.Api;

namespace Avalonia_UI.Models;

public sealed record WorkflowExportDocument
{
    public const string CurrentFormat = "flowweaver.workflow.v1";

    [JsonPropertyName("export_format")]
    public string ExportFormat { get; init; } = CurrentFormat;

    [JsonPropertyName("exported_at")]
    public DateTimeOffset ExportedAt { get; init; }

    [JsonPropertyName("workflow")]
    public WorkflowExportWorkflow Workflow { get; init; } = new();
}

public sealed record WorkflowExportWorkflow
{
    [JsonPropertyName("workflow_id")]
    public string WorkflowId { get; init; } = string.Empty;

    [JsonPropertyName("name")]
    public string Name { get; init; } = string.Empty;

    [JsonPropertyName("revision_id")]
    public string RevisionId { get; init; } = string.Empty;

    [JsonPropertyName("version")]
    public int Version { get; init; }

    [JsonPropertyName("definition_hash")]
    public string DefinitionHash { get; init; } = string.Empty;

    [JsonPropertyName("status")]
    public string Status { get; init; } = string.Empty;

    [JsonPropertyName("definition")]
    public JsonElement Definition { get; init; }
}

public static class WorkflowExportDocumentBuilder
{
    private const string FileSuffix = ".flowweaver-workflow.json";

    public static WorkflowExportDocument Create(
        WorkflowDefinitionDto workflow,
        DateTimeOffset exportedAt)
    {
        return new WorkflowExportDocument
        {
            ExportedAt = exportedAt.ToUniversalTime(),
            Workflow = new WorkflowExportWorkflow
            {
                WorkflowId = workflow.WorkflowId,
                Name = workflow.Name,
                RevisionId = workflow.RevisionId,
                Version = workflow.Version,
                DefinitionHash = workflow.DefinitionHash,
                Status = workflow.Status,
                Definition = workflow.Definition.Clone(),
            },
        };
    }

    public static string Serialize(WorkflowDefinitionDto workflow, DateTimeOffset exportedAt)
    {
        return JsonSerializer.Serialize(
            Create(workflow, exportedAt),
            FlowWeaverJson.Options);
    }

    public static string SuggestedFileName(WorkflowDefinitionDto workflow)
    {
        var name = SanitizeFileName(workflow.Name);
        return $"{name}_v{workflow.Version}{FileSuffix}";
    }

    private static string SanitizeFileName(string value)
    {
        var invalid = Path.GetInvalidFileNameChars();
        var sanitized = new string(
                value
                    .Trim()
                    .Select(ch => char.IsControl(ch) || invalid.Contains(ch) ? '_' : ch)
                    .ToArray())
            .Trim(' ', '.', '_');
        return string.IsNullOrWhiteSpace(sanitized)
            ? "workflow"
            : sanitized;
    }
}

public sealed record WorkflowImportDocumentReadResult(
    bool Succeeded,
    string? Name,
    JsonElement Definition,
    string? ErrorMessageKey)
{
    public static WorkflowImportDocumentReadResult Success(
        string name,
        JsonElement definition)
    {
        return new WorkflowImportDocumentReadResult(true, name, definition, null);
    }

    public static WorkflowImportDocumentReadResult Failure(string errorMessageKey)
    {
        return new WorkflowImportDocumentReadResult(false, null, default, errorMessageKey);
    }
}

public static class WorkflowImportDocumentReader
{
    public static WorkflowImportDocumentReadResult Read(string content)
    {
        JsonDocument document;
        try
        {
            document = JsonDocument.Parse(content);
        }
        catch (JsonException)
        {
            return WorkflowImportDocumentReadResult.Failure("workflow.import_invalid_json");
        }

        using (document)
        {
            var root = document.RootElement;
            if (root.ValueKind != JsonValueKind.Object)
            {
                return WorkflowImportDocumentReadResult.Failure("workflow.import_invalid_document");
            }

            if (!root.TryGetProperty("export_format", out var formatElement) ||
                formatElement.ValueKind != JsonValueKind.String ||
                !string.Equals(
                    formatElement.GetString(),
                    WorkflowExportDocument.CurrentFormat,
                    StringComparison.Ordinal))
            {
                return WorkflowImportDocumentReadResult.Failure("workflow.import_unsupported_format");
            }

            if (!root.TryGetProperty("workflow", out var workflowElement) ||
                workflowElement.ValueKind != JsonValueKind.Object)
            {
                return WorkflowImportDocumentReadResult.Failure("workflow.import_missing_workflow");
            }

            if (!workflowElement.TryGetProperty("name", out var nameElement) ||
                nameElement.ValueKind != JsonValueKind.String ||
                string.IsNullOrWhiteSpace(nameElement.GetString()))
            {
                return WorkflowImportDocumentReadResult.Failure("workflow.import_missing_name");
            }

            if (!workflowElement.TryGetProperty("definition", out var definitionElement) ||
                definitionElement.ValueKind is JsonValueKind.Undefined or JsonValueKind.Null)
            {
                return WorkflowImportDocumentReadResult.Failure("workflow.import_missing_definition");
            }

            return WorkflowImportDocumentReadResult.Success(
                nameElement.GetString()!.Trim(),
                definitionElement.Clone());
        }
    }
}
