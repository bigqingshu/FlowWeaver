using System;
using System.Text.Json;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class WorkflowExportDocumentTests
{
    [TestMethod]
    public void SerializeIncludesFormatMetadataAndWorkflowDefinition()
    {
        var exportedAt = DateTimeOffset.Parse("2026-06-29T01:02:03Z");
        using var definition = JsonDocument.Parse(
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "generate", "node_type": "GenerateTestTableNode"}
              ],
              "connections": []
            }
            """);
        var workflow = new WorkflowDefinitionDto
        {
            WorkflowId = "wf-1",
            Name = "Daily Load",
            RevisionId = "rev-1",
            Version = 2,
            DefinitionHash = "hash-1",
            Status = "ACTIVE",
            Definition = definition.RootElement.Clone(),
        };

        var json = WorkflowExportDocumentBuilder.Serialize(workflow, exportedAt);

        using var export = JsonDocument.Parse(json);
        var root = export.RootElement;
        Assert.AreEqual(
            WorkflowExportDocument.CurrentFormat,
            root.GetProperty("export_format").GetString());
        Assert.AreEqual(exportedAt, root.GetProperty("exported_at").GetDateTimeOffset());
        var exportedWorkflow = root.GetProperty("workflow");
        Assert.AreEqual("wf-1", exportedWorkflow.GetProperty("workflow_id").GetString());
        Assert.AreEqual("Daily Load", exportedWorkflow.GetProperty("name").GetString());
        Assert.AreEqual("rev-1", exportedWorkflow.GetProperty("revision_id").GetString());
        Assert.AreEqual(2, exportedWorkflow.GetProperty("version").GetInt32());
        Assert.AreEqual("hash-1", exportedWorkflow.GetProperty("definition_hash").GetString());
        Assert.AreEqual("ACTIVE", exportedWorkflow.GetProperty("status").GetString());
        Assert.AreEqual(
            "GenerateTestTableNode",
            exportedWorkflow
                .GetProperty("definition")
                .GetProperty("nodes")[0]
                .GetProperty("node_type")
                .GetString());
    }

    [TestMethod]
    public void SuggestedFileNameUsesWorkflowNameAndVersion()
    {
        var workflow = new WorkflowDefinitionDto
        {
            Name = "Daily\u0001Load",
            Version = 3,
        };

        var fileName = WorkflowExportDocumentBuilder.SuggestedFileName(workflow);

        Assert.AreEqual("Daily_Load_v3.flowweaver-workflow.json", fileName);
    }

    [TestMethod]
    public void SuggestedFileNameFallsBackForBlankWorkflowName()
    {
        var workflow = new WorkflowDefinitionDto
        {
            Name = "   ",
            Version = 1,
        };

        var fileName = WorkflowExportDocumentBuilder.SuggestedFileName(workflow);

        Assert.AreEqual("workflow_v1.flowweaver-workflow.json", fileName);
    }
}
