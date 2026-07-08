using System.Text.Json;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

internal static class TemplateWorkflowDefinitions
{
    public static JsonDocument CreateGeneratedTable(
        string generateRowsDisplayName,
        string keepAmountGreaterThanOneDisplayName)
    {
        var definition = new
        {
            schema_version = "1.0",
            nodes = new object[]
            {
                new
                {
                    node_instance_id = "generate",
                    node_type = "GenerateTestTableNode",
                    node_version = "1.0",
                    display_name = generateRowsDisplayName,
                    config = new
                    {
                        rows = 3,
                        columns = new[] { "row_id", "amount" },
                        seed = 0,
                    },
                },
                new
                {
                    node_instance_id = "filter",
                    node_type = "FilterRowsNode",
                    node_version = "1.0",
                    display_name = keepAmountGreaterThanOneDisplayName,
                    config = new
                    {
                        field = "amount",
                        @operator = "GT",
                        value = 1.0,
                    },
                },
            },
            connections = new[]
            {
                new
                {
                    connection_id = "generate_to_filter",
                    source_node_id = "generate",
                    source_port = "out",
                    target_node_id = "filter",
                    target_port = "in",
                },
            },
        };

        return JsonSerializer.SerializeToDocument(definition, FlowWeaverJson.Options);
    }
}
