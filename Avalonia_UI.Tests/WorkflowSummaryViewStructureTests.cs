using System;
using System.IO;
using System.Linq;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class WorkflowSummaryViewStructureTests
{
    [TestMethod]
    public void NodeTemplateShowsEditorStatusAsReadOnlyText()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowNodeListView.axaml");

        StringAssert.Contains(xaml, "Text=\"{Binding WorkflowNodesSectionText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding WorkflowDefinitionDraftNodeCountText}\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding WorkflowDefinitionDraftNodes}\"");
        StringAssert.Contains(xaml, "SelectedItem=\"{Binding SelectedWorkflowDefinitionNode}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding NodeEditorStatusText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding ConfigJson}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding WorkflowDefinitionValidationMessage}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding WorkflowDefinitionValidationErrorMessage}\"");
        StringAssert.Contains(xaml, "RowDefinitions=\"Auto,Auto,Auto,Auto\"");
        Assert.IsFalse(xaml.Contains("NodeEditorStatusText}\" Command=", StringComparison.Ordinal));
    }

    [TestMethod]
    public void WorkflowSummaryViewDoesNotOwnNodeSelectionList()
    {
        var summaryXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");
        var configXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSelectedNodeConfigView.axaml");

        StringAssert.Contains(summaryXaml, "<workflow:WorkflowSelectedNodeConfigView />");
        StringAssert.Contains(configXaml, "Text=\"{Binding SelectedNodeConfigDraftSummaryText}\"");
        StringAssert.Contains(
            configXaml,
            "ItemsSource=\"{Binding SelectedNodeConfigEditableInputFields}\"");
        Assert.IsFalse(
            summaryXaml.Contains("ItemsSource=\"{Binding WorkflowDefinitionDetail.Nodes}\"", StringComparison.Ordinal));
        Assert.IsFalse(
            summaryXaml.Contains("SelectedItem=\"{Binding SelectedWorkflowDefinitionNode}\"", StringComparison.Ordinal));
    }

    [TestMethod]
    public void NodeTemplateDoesNotIntroduceNodeEditingActions()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        Assert.IsFalse(xaml.Contains("EditNode", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("ConfigureNode", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("OpenNodeEditor", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("SaveNode", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("ListNodeDefinitionsAsync", StringComparison.Ordinal));
    }

    [TestMethod]
    public void NodeConfigEditorBindsToInputFieldsAndApplyCommand()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSelectedNodeConfigView.axaml");

        StringAssert.Contains(
            xaml,
            "ItemsSource=\"{Binding SelectedNodeConfigEditableInputFields}\"");
        StringAssert.Contains(
            xaml,
            "Command=\"{Binding ApplySelectedNodeConfigDraftCommand}\"");
        StringAssert.Contains(
            xaml,
            "x:DataType=\"vm:NodeConfigEditableFieldInputViewModel\"");
        StringAssert.Contains(xaml, "Text=\"{Binding InputValue, Mode=TwoWay");
        StringAssert.Contains(xaml, "SelectedItem=\"{Binding InputValue, Mode=TwoWay}\"");
    }

    [TestMethod]
    public void NodeConfigEditorUsesViewHelperBindingsWithoutConverters()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSelectedNodeConfigView.axaml");

        StringAssert.Contains(
            xaml,
            "IsVisible=\"{Binding HasSelectedNodeConfigEditableInputFields}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding DisplayLabel}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding TypeText}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding RequiredText}\"");
        StringAssert.Contains(xaml, "IsVisible=\"{Binding IsTextInput}\"");
        StringAssert.Contains(xaml, "IsVisible=\"{Binding IsEnumInput}\"");
        StringAssert.Contains(xaml, "IsVisible=\"{Binding IsBooleanInput}\"");
        StringAssert.Contains(xaml, "ItemsSource=\"{Binding BooleanValues}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding WarningText}\"");
        Assert.IsFalse(xaml.Contains("Converter=", StringComparison.Ordinal));
    }

    [TestMethod]
    public void StructuredEditFormsBindToDraftInputsAndCommands()
    {
        var summaryXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");
        var addNodeXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowAddNodeView.axaml");
        var nodeListXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowNodeListView.axaml");

        StringAssert.Contains(summaryXaml, "<workflow:WorkflowAddNodeView />");
        StringAssert.Contains(addNodeXaml, "Text=\"{Binding AddNodeText}\"");
        StringAssert.Contains(addNodeXaml, "Content=\"{Binding AddNodeText}\"");
        StringAssert.Contains(
            addNodeXaml,
            "Command=\"{Binding AddWorkflowDefinitionDraftNodeCommand}\"");
        StringAssert.Contains(nodeListXaml, "Content=\"{Binding DeleteNodeText}\"");
        StringAssert.Contains(summaryXaml, "Text=\"{Binding AddConnectionText}\"");
        StringAssert.Contains(summaryXaml, "Text=\"{Binding DeleteConnectionText}\"");
        StringAssert.Contains(addNodeXaml, "Text=\"{Binding NodeInstanceIdText}\"");
        StringAssert.Contains(addNodeXaml, "Text=\"{Binding NodeTypeText}\"");
        StringAssert.Contains(addNodeXaml, "Text=\"{Binding NodeVersionText}\"");
        StringAssert.Contains(addNodeXaml, "Text=\"{Binding DisplayNameText}\"");
        StringAssert.Contains(addNodeXaml, "Text=\"{Binding ConfigJsonText}\"");
        StringAssert.Contains(addNodeXaml, "Text=\"{Binding NewDraftNodeInstanceId, Mode=TwoWay");
        StringAssert.Contains(addNodeXaml, "Text=\"{Binding NewDraftNodeType, Mode=TwoWay");
        StringAssert.Contains(addNodeXaml, "Text=\"{Binding NewDraftNodeVersion, Mode=TwoWay");
        StringAssert.Contains(addNodeXaml, "Text=\"{Binding NewDraftNodeDisplayName, Mode=TwoWay");
        StringAssert.Contains(addNodeXaml, "Text=\"{Binding NewDraftNodeConfigJson, Mode=TwoWay");
        StringAssert.Contains(
            addNodeXaml,
            "ItemsSource=\"{Binding NodeDefinitions}\"");
        StringAssert.Contains(
            addNodeXaml,
            "SelectedItem=\"{Binding SelectedNewDraftNodeDefinition, Mode=TwoWay}\"");
        StringAssert.Contains(
            addNodeXaml,
            "ToolTip.Tip=\"{Binding RefreshNodeDefinitionsDisabledReasonText}\"");
        StringAssert.Contains(
            addNodeXaml,
            "Command=\"{Binding RefreshNodeDefinitionsCommand}\"");
        StringAssert.Contains(
            addNodeXaml,
            "x:DataType=\"vm:NodeDefinitionListItemViewModel\"");
        StringAssert.Contains(
            nodeListXaml,
            "Command=\"{Binding DeleteWorkflowDefinitionDraftNodeCommand}\"");
        Assert.IsFalse(
            addNodeXaml.Contains(
                "Text=\"{Binding SelectedWorkflowDefinitionDraftNodeInstanceId, Mode=TwoWay",
                StringComparison.Ordinal));

        StringAssert.Contains(summaryXaml, "Text=\"{Binding ConnectionIdText}\"");
        StringAssert.Contains(summaryXaml, "Text=\"{Binding SourceNodeText}\"");
        StringAssert.Contains(summaryXaml, "Text=\"{Binding SourcePortText}\"");
        StringAssert.Contains(summaryXaml, "Text=\"{Binding TargetNodeText}\"");
        StringAssert.Contains(summaryXaml, "Text=\"{Binding TargetPortText}\"");
        StringAssert.Contains(summaryXaml, "Text=\"{Binding NewDraftConnectionId, Mode=TwoWay");
        StringAssert.Contains(summaryXaml, "Text=\"{Binding NewDraftConnectionSourceNodeId, Mode=TwoWay");
        StringAssert.Contains(summaryXaml, "Text=\"{Binding NewDraftConnectionSourcePort, Mode=TwoWay");
        StringAssert.Contains(summaryXaml, "Text=\"{Binding NewDraftConnectionTargetNodeId, Mode=TwoWay");
        StringAssert.Contains(summaryXaml, "Text=\"{Binding NewDraftConnectionTargetPort, Mode=TwoWay");
        StringAssert.Contains(
            summaryXaml,
            "ItemsSource=\"{Binding WorkflowDefinitionDraftStructure.Nodes}\"");
        StringAssert.Contains(
            summaryXaml,
            "SelectedItem=\"{Binding SelectedNewDraftConnectionSourceNode, Mode=TwoWay}\"");
        StringAssert.Contains(
            summaryXaml,
            "SelectedItem=\"{Binding SelectedNewDraftConnectionTargetNode, Mode=TwoWay}\"");
        StringAssert.Contains(
            summaryXaml,
            "x:DataType=\"models:WorkflowDefinitionDraftNode\"");
        StringAssert.Contains(summaryXaml, "Text=\"{Binding NodeTypeDisplayName}\"");
        StringAssert.Contains(
            summaryXaml,
            "Command=\"{Binding AddWorkflowDefinitionDraftConnectionCommand}\"");
        StringAssert.Contains(
            summaryXaml,
            "Text=\"{Binding SelectedWorkflowDefinitionDraftConnectionId, Mode=TwoWay");
        StringAssert.Contains(
            summaryXaml,
            "Command=\"{Binding DeleteWorkflowDefinitionDraftConnectionCommand}\"");
        Assert.IsFalse(summaryXaml.Contains("Converter=", StringComparison.Ordinal));
        Assert.IsFalse(addNodeXaml.Contains("Converter=", StringComparison.Ordinal));
    }

    [TestMethod]
    public void WorkflowDefinitionCardOmitsRevisionHistoryList()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        StringAssert.Contains(xaml, "Text=\"{Binding WorkflowDefinitionDetail.RevisionId}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding WorkflowDefinitionDetail.DefinitionHash}\"");
        StringAssert.Contains(xaml, "Text=\"{Binding WorkflowDefinitionDetail.UpdatedAtText}\"");
        Assert.IsFalse(xaml.Contains("WorkflowDefinitionDetail.Revisions", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("WorkflowRevisionListItemViewModel", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("SelectedRevision", StringComparison.Ordinal));
    }

    [TestMethod]
    public void WorkflowPageKeepsDefinitionWorkspaceWithDedicatedNodeListColumn()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Pages",
            "WorkflowPage.axaml");

        StringAssert.Contains(xaml, "ColumnDefinitions=\"340,*,340\"");
        StringAssert.Contains(xaml, "<workflow:WorkflowListView Grid.Column=\"0\" />");
        StringAssert.Contains(xaml, "<workflow:WorkflowSummaryView Grid.Column=\"1\" />");
        StringAssert.Contains(xaml, "<workflow:WorkflowNodeListView Grid.Column=\"2\" />");
        Assert.IsFalse(xaml.Contains("<workflow:WorkflowEditorView", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("<workflow:WorkflowNodeCatalogView", StringComparison.Ordinal));
    }

    [TestMethod]
    public void NodeActionGroupContainsDraftMutationButtonsAndAdvancedToggle()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowNodeListView.axaml");
        var addNodeXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowAddNodeView.axaml");
        var summaryXaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        StringAssert.Contains(xaml, "Text=\"{Binding NodeActionsSectionText}\"");
        StringAssert.Contains(xaml, "<WrapPanel Orientation=\"Horizontal\"");
        StringAssert.Contains(
            addNodeXaml,
            "Command=\"{Binding AddWorkflowDefinitionDraftNodeCommand}\"");
        StringAssert.Contains(xaml, "Content=\"{Binding MoveNodeUpText}\"");
        StringAssert.Contains(
            xaml,
            "Command=\"{Binding MoveSelectedWorkflowDefinitionDraftNodeUpCommand}\"");
        StringAssert.Contains(xaml, "Content=\"{Binding MoveNodeDownText}\"");
        StringAssert.Contains(
            xaml,
            "Command=\"{Binding MoveSelectedWorkflowDefinitionDraftNodeDownCommand}\"");
        StringAssert.Contains(xaml, "Content=\"{Binding DeleteNodeText}\"");
        StringAssert.Contains(
            xaml,
            "Command=\"{Binding DeleteWorkflowDefinitionDraftNodeCommand}\"");
        StringAssert.Contains(xaml, "Content=\"{Binding ShowAdvancedDraftJsonText}\"");
        StringAssert.Contains(
            xaml,
            "IsChecked=\"{Binding IsWorkflowDraftJsonAdvancedVisible, Mode=TwoWay}\"");
        StringAssert.Contains(
            summaryXaml,
            "<workflow:WorkflowEditorView IsVisible=\"{Binding IsWorkflowDraftJsonAdvancedVisible}\"");
        Assert.IsFalse(
            summaryXaml.Contains("Text=\"{Binding NodeActionsSectionText}\"", StringComparison.Ordinal));
        Assert.IsFalse(
            summaryXaml.Contains("Content=\"{Binding ShowAdvancedDraftJsonText}\"", StringComparison.Ordinal));
        Assert.IsFalse(
            xaml.Contains("Content=\"{Binding AddNodeText}\"", StringComparison.Ordinal));

        var actionGroupIndex = xaml.IndexOf(
            "Text=\"{Binding NodeActionsSectionText}\"",
            StringComparison.Ordinal);
        var advancedToggleIndex = xaml.IndexOf(
            "Content=\"{Binding ShowAdvancedDraftJsonText}\"",
            StringComparison.Ordinal);
        var editorIndex = summaryXaml.IndexOf(
            "<workflow:WorkflowEditorView IsVisible=\"{Binding IsWorkflowDraftJsonAdvancedVisible}\"",
            StringComparison.Ordinal);
        Assert.IsTrue(
            actionGroupIndex >= 0 && advancedToggleIndex > actionGroupIndex,
            "The draft JSON toggle should live inside the node action group.");
        Assert.IsGreaterThanOrEqualTo(
            0,
            editorIndex,
            "The draft JSON editor should remain controlled by the node action group's advanced toggle.");
    }

    [TestMethod]
    public void ConnectionsSectionIsCollapsedBehindToggleByDefault()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        StringAssert.Contains(xaml, "Content=\"{Binding ShowConnectionsText}\"");
        StringAssert.Contains(
            xaml,
            "IsChecked=\"{Binding IsWorkflowConnectionsAdvancedVisible, Mode=TwoWay}\"");
        StringAssert.Contains(
            xaml,
            "IsVisible=\"{Binding IsWorkflowConnectionsAdvancedVisible}\"");
        Assert.IsFalse(xaml.Contains("IsWorkflowConnectionsAdvancedVisible = true", StringComparison.Ordinal));
    }

    [TestMethod]
    public void MiddleColumnLayoutKeepsStructuredEditAreasCompactAndScrollable()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        StringAssert.Contains(xaml, "<ScrollViewer VerticalScrollBarVisibility=\"Auto\"");
        StringAssert.Contains(xaml, "<StackPanel Spacing=\"10\">");
        StringAssert.Contains(xaml, "MaxHeight=\"140\"");
        Assert.IsFalse(xaml.Contains("RowDefinitions=\"Auto,*,*\"", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("RowDefinitions=\"Auto,*,Auto,Auto,Auto\"", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("RowDefinitions=\"Auto,*,Auto\"", StringComparison.Ordinal));
        Assert.IsFalse(xaml.Contains("MinHeight=\"100\"", StringComparison.Ordinal));
    }

    [TestMethod]
    public void WorkflowSummaryViewHostsAddNodeAboveSelectedNodeConfig()
    {
        var xaml = ReadSourceFile(
            "Avalonia_UI",
            "Views",
            "Components",
            "Workflow",
            "WorkflowSummaryView.axaml");

        var addNodeIndex = xaml.IndexOf("<workflow:WorkflowAddNodeView />", StringComparison.Ordinal);
        var configIndex = xaml.IndexOf("<workflow:WorkflowSelectedNodeConfigView />", StringComparison.Ordinal);

        Assert.AreNotEqual(
            -1,
            addNodeIndex,
            "The middle column should host the dedicated add-node area.");
        Assert.AreNotEqual(
            -1,
            configIndex,
            "The middle column should host the dedicated selected-node config area.");
        Assert.IsLessThan(
            configIndex,
            addNodeIndex,
            "The add-node area should stay above the selected-node config area.");
    }

    private static string ReadSourceFile(params string[] pathParts)
    {
        var repoRoot = GetRepoRoot();
        return File.ReadAllText(Path.Combine(pathParts.Prepend(repoRoot).ToArray()));
    }

    private static string GetRepoRoot()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            if (Directory.Exists(Path.Combine(directory.FullName, "Avalonia_UI"))
                && Directory.Exists(Path.Combine(directory.FullName, "Avalonia_UI.Tests")))
            {
                return directory.FullName;
            }

            directory = directory.Parent;
        }

        throw new DirectoryNotFoundException("Could not locate FlowWeaver repository root.");
    }
}
